import os
import sys
import pickle
import random
from pathlib import Path
import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset

# ลองโหลด sklearn หากลงสำเร็จ
try:
    from sklearn.model_selection import train_test_split
    from sklearn.svm import SVC
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import classification_report, accuracy_score
    from sklearn.utils.class_weight import compute_class_weight
except ImportError:
    print("Error: ไม่พบไลบรารี scikit-learn")
    print("กรุณารันคำสั่ง: pip install scikit-learn")
    sys.exit(1)

# ตั้งค่า
BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "models"
LABELS = ["bronchitis", "croup", "normal", "pneumonia"]

# 1. นิยามโมเดลฝั่ง PyTorch เพื่อเปรียบเทียบ
class PyTorchLogisticRegression(nn.Module):
    def __init__(self, input_dim=512, num_classes=4):
        super().__init__()
        self.linear = nn.Linear(input_dim, num_classes)
    def forward(self, x):
        return self.linear(x)

class PyTorchRegularizedMLP(nn.Module):
    def __init__(self, input_dim=512, hidden_dim=64, num_classes=4):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.5), # ดร็อปหนักขึ้น
            nn.Linear(hidden_dim, num_classes)
        )
    def forward(self, x):
        return self.net(x)

class SimpleDataset(Dataset):
    def __init__(self, x, y):
        self.x = torch.tensor(x, dtype=torch.float32)
        self.y = torch.tensor(y, dtype=torch.long)
    def __len__(self):
        return len(self.y)
    def __getitem__(self, idx):
        return self.x[idx], self.y[idx]

import copy

def train_pytorch_model(model, train_x, train_y, val_x, val_y, class_weights, epochs=100, lr=0.001):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = model.to(device)
    
    train_ds = SimpleDataset(train_x, train_y)
    val_ds = SimpleDataset(val_x, val_y)
    train_loader = DataLoader(train_ds, batch_size=16, shuffle=True)
    
    criterion = nn.CrossEntropyLoss(weight=torch.tensor(class_weights, dtype=torch.float32).to(device))
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.05) # เพิ่ม weight decay เพื่อลด overfit
    
    best_acc = 0.0
    best_weights = None
    
    for epoch in range(epochs):
        model.train()
        for x_batch, y_batch in train_loader:
            x_batch, y_batch = x_batch.to(device), y_batch.to(device)
            optimizer.zero_grad()
            outputs = model(x_batch)
            loss = criterion(outputs, y_batch)
            loss.backward()
            optimizer.step()
            
        # ประเมินผล
        model.eval()
        correct = 0
        total = 0
        with torch.no_grad():
            outputs = model(torch.tensor(val_x, dtype=torch.float32).to(device))
            preds = outputs.argmax(dim=1)
            correct = (preds.cpu().numpy() == val_y).sum()
            total = len(val_y)
            
        val_acc = correct / total
        if val_acc > best_acc:
            best_acc = val_acc
            best_weights = copy.deepcopy(model.state_dict())
            
    if best_weights is not None:
        model.load_state_dict(best_weights)
    return best_acc

def main():
    cache_path = MODEL_DIR / "hear_embeddings.pt"
    if not cache_path.exists():
        print(f"Error: ไม่พบไฟล์แคชที่ {cache_path} กรุณารันสคริปต์สแกนเสียงรอบแรกก่อน")
        return
        
    print(f"กำลังโหลดข้อมูลแคชจาก {cache_path}...")
    cache_data = torch.load(cache_path, weights_only=False)
    X = cache_data["embeddings"]
    y = cache_data["labels"]
    
    print(f"โหลดสำเร็จ! ขนาดข้อมูล X: {X.shape}, y: {y.shape}")
    
    # แบ่งข้อมูลแบบ Stratified Split (80/20) เพื่อให้แน่ใจว่า Croup และ Normal มีสัดส่วนเท่ากันใน train/val
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )
    
    print("\nจำนวนข้อมูลแยกตามโรคในชุดข้อมูล:")
    for i, name in enumerate(LABELS):
        train_count = sum(y_train == i)
        val_count = sum(y_val == i)
        print(f"  - {name:10s} | Train: {train_count:3d} ไฟล์ | Val: {val_count:3d} ไฟล์")
        
    # คำนวณ class weight เพื่อชดเชยข้อมูลโรคที่ไม่เท่ากัน
    class_weights = compute_class_weight(
        class_weight='balanced', classes=np.unique(y_train), y=y_train
    )
    
    results = {}
    
    # ----------------------------------------------------
    # Model 1: PyTorch Logistic Regression (Linear)
    # ----------------------------------------------------
    pt_linear = PyTorchLogisticRegression()
    acc_pt_linear = train_pytorch_model(pt_linear, X_train, y_train, X_val, y_val, class_weights, epochs=120, lr=0.001)
    results["PyTorch Logistic Regression"] = (acc_pt_linear, pt_linear)
    
    # ----------------------------------------------------
    # Model 2: PyTorch MLP (Regularized)
    # ----------------------------------------------------
    pt_mlp = PyTorchRegularizedMLP()
    acc_pt_mlp = train_pytorch_model(pt_mlp, X_train, y_train, X_val, y_val, class_weights, epochs=120, lr=0.001)
    results["PyTorch Regularized MLP"] = (acc_pt_mlp, pt_mlp)
    
    # ----------------------------------------------------
    # Model 3: SVM (Linear Kernel)
    # ----------------------------------------------------
    svm_linear = SVC(kernel='linear', class_weight='balanced', C=0.5, probability=True, random_state=42)
    svm_linear.fit(X_train, y_train)
    preds_svm_linear = svm_linear.predict(X_val)
    acc_svm_linear = accuracy_score(y_val, preds_svm_linear)
    results["SVM (Linear Kernel)"] = (acc_svm_linear, svm_linear)
    
    # ----------------------------------------------------
    # Model 4: SVM (RBF Kernel)
    # ----------------------------------------------------
    svm_rbf = SVC(kernel='rbf', class_weight='balanced', C=2.0, gamma='scale', probability=True, random_state=42)
    svm_rbf.fit(X_train, y_train)
    preds_svm_rbf = svm_rbf.predict(X_val)
    acc_svm_rbf = accuracy_score(y_val, preds_svm_rbf)
    results["SVM (RBF Kernel)"] = (acc_svm_rbf, svm_rbf)
    
    # ----------------------------------------------------
    # Model 5: Random Forest
    # ----------------------------------------------------
    rf = RandomForestClassifier(n_estimators=150, max_depth=6, class_weight='balanced', random_state=42)
    rf.fit(X_train, y_train)
    preds_rf = rf.predict(X_val)
    acc_rf = accuracy_score(y_val, preds_rf)
    results["Random Forest"] = (acc_rf, rf)
    
    # ----------------------------------------------------
    # ตารางเปรียบเทียบผลลัพธ์
    # ----------------------------------------------------
    print("\n" + "="*50)
    print(f"{'โมเดล Classifier':<30} | {'Validation Accuracy':<18}")
    print("="*50)
    for model_name, (acc, _) in sorted(results.items(), key=lambda item: item[1][0], reverse=True):
        print(f"{model_name:<30} | {acc*100:.2f}%")
    print("="*50)
    
    # 5. หาโมเดลที่ดีที่สุดและบันทึก
    best_name, (best_acc, best_model) = max(results.items(), key=lambda item: item[1][0])
    print(f"\nโมเดลที่ดีที่สุดคือ: {best_name} (Acc: {best_acc*100:.2f}%)")
    
    # การคำนวณและแสดงผลการทำนายบน Validation Set
    if "SVM" in best_name or "Random Forest" in best_name:
        preds_best = best_model.predict(X_val)
    else:
        # สำหรับโมเดล PyTorch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        best_model.eval()
        with torch.no_grad():
            outputs = best_model(torch.tensor(X_val, dtype=torch.float32).to(device))
            preds_best = outputs.argmax(dim=1).cpu().numpy()
            
    print("\nรายงานผลการวิเคราะห์คลาสโรค (Detailed Classification Report):")
    print(classification_report(y_val, preds_best, target_names=LABELS))
    
    # บันทึกโมเดล
    if "SVM" in best_name or "Random Forest" in best_name:
        save_path = MODEL_DIR / "hear_classifier.pkl"
        with open(save_path, 'wb') as f:
            pickle.dump({
                "model": best_model,
                "model_type": "sklearn",
                "labels": LABELS
            }, f)
        print(f"บันทึกโมเดล scikit-learn สำเร็จที่: {save_path}")
    else:
        save_path = MODEL_DIR / "hear_classifier.pt"
        torch.save({
            "model_state": best_model.state_dict(),
            "model_type": "pytorch",
            "architecture": best_model.__class__.__name__,
            "labels": LABELS
        }, save_path)
        print(f"บันทึกโมเดล PyTorch สำเร็จที่: {save_path}")

if __name__ == "__main__":
    main()
