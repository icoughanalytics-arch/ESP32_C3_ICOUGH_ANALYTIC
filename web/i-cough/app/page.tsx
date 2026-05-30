"use client";

import { DotLottieReact } from '@lottiefiles/dotlottie-react';

export default function Home() {
  return (
    <div className="w-64 h-64">
      <DotLottieReact
        src="/Lung infection.json"
        loop
        autoplay
      />
    </div>
  );
}
