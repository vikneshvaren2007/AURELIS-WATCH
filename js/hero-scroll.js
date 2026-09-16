/* ==========================================================================
   AURELIS — Apple-Style Hero Scrollytelling Engine
   Dynamically discovers Frame 2 sequence, preloads instantly, and animates
   strictly via scroll kinematics with requestAnimationFrame.
   ========================================================================== */

(function () {
  const canvas = document.getElementById("watchCanvas");
  if (!canvas) return;

  const ctx = canvas.getContext("2d", { alpha: false, desynchronized: true });
  const loader = document.getElementById("loader");
  const bar = document.getElementById("loaderBar");
  const percentEl = document.getElementById("loaderPercent");
  const statusEl = document.getElementById("loaderStatus");
  const nav = document.getElementById("mainNav");
  const introWrap = document.getElementById("heroIntro");
  const outroWrap = document.getElementById("heroOutro");
  const outroOverlay = document.getElementById("heroOutroOverlay");
  const scrollCue = document.getElementById("heroScrollCue");
  const progressNum = document.getElementById("heroProgressNum");
  const heroSection = document.getElementById("hero");

  let frameUrls = [];
  let frameCount = 240;
  let images = [];
  let loadedCount = 0;
  let currentFrame = 0;
  let targetFrame = 0;
  let isRunning = false;
  let animationId = null;

  // Track nav scroll state
  function updateNav() {
    if (!nav) return;
    if (window.scrollY > 40) {
      nav.classList.add("scrolled");
    } else {
      nav.classList.remove("scrolled");
    }
  }
  window.addEventListener("scroll", updateNav, { passive: true });
  updateNav();

  // Dynamic frame discovery
  async function fetchFrameList() {
    try {
      const res = await fetch("/api/frames");
      if (res.ok) {
        const data = await res.json();
        if (data.frames && data.frames.length > 0) {
          frameUrls = data.frames;
          frameCount = data.frames.length;
          return;
        }
      }
    } catch (e) {
      console.warn("API frame discovery unavailable, falling back to static sequence", e);
    }

    // High-fidelity fallback for original homepage hero frames
    frameUrls = [];
    frameCount = 240;
    for (let i = 1; i <= 240; i++) {
      const padded = String(i).padStart(4, "0");
      frameUrls.push(`./frames/frame_${padded}.jpg`);
    }
  }

  // Load an individual frame
  function loadFrame(index) {
    return new Promise((resolve) => {
      if (images[index]) {
        return resolve(images[index]);
      }
      const img = new Image();
      img.decoding = "async";
      img.src = frameUrls[index];
      img.onload = () => {
        images[index] = img;
        loadedCount++;
        resolve(img);
      };
      img.onerror = () => {
        // Fallback retry with URL encoding if needed
        const encodedSrc = frameUrls[index].replace(" ", "%20");
        if (img.src !== encodedSrc) {
          img.src = encodedSrc;
        } else {
          resolve(null);
        }
      };
    });
  }

  // Progressively stream remaining frames in background
  async function streamRemainingFrames(start) {
    const batchSize = 6;
    for (let i = start; i < frameCount; i += batchSize) {
      const batch = [];
      for (let j = 0; j < batchSize && (i + j) < frameCount; j++) {
        batch.push(loadFrame(i + j));
      }
      await Promise.all(batch);
      // Brief yield so the UI thread and render loop stay completely buttery
      await new Promise((r) => setTimeout(r, 16));
    }
  }

  // High-DPI responsive canvas sizing
  function resize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(window.innerWidth * dpr);
    canvas.height = Math.round(window.innerHeight * dpr);
    canvas.style.width = window.innerWidth + "px";
    canvas.style.height = window.innerHeight + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    drawFrame(currentFrame);
  }

  // Precision canvas drawing with aspect ratio protection
  function drawFrame(index) {
    const safeIndex = Math.max(0, Math.min(frameCount - 1, Math.round(index)));
    // Use nearest loaded image or frame 0
    let img = images[safeIndex];
    if (!img) {
      // Find nearest loaded frame
      for (let offset = 1; offset < 20; offset++) {
        if (images[safeIndex - offset]) { img = images[safeIndex - offset]; break; }
        if (images[safeIndex + offset]) { img = images[safeIndex + offset]; break; }
      }
    }
    if (!img) img = images[0];
    if (!img) return;

    const cw = window.innerWidth;
    const ch = window.innerHeight;

    // Deep luxury background fill (#080706)
    ctx.fillStyle = "#080706";
    ctx.fillRect(0, 0, cw, ch);

    // Maintain aspect ratio without stretching or distorting the watch
    const screenAspect = cw / ch;
    const imgAspect = (img.naturalWidth || 1920) / (img.naturalHeight || 1080);
    let scale;

    if (screenAspect < 1) {
      // Mobile portrait: fit watch completely without clipping exploded view labels
      // Since background is #080706, pillarbox is 100% invisible
      scale = Math.min(cw / (img.naturalWidth || 1920), ch / (img.naturalHeight || 1080)) * 1.08;
    } else {
      // Desktop / Landscape: luxury full-bleed cover
      scale = Math.max(cw / (img.naturalWidth || 1920), ch / (img.naturalHeight || 1080));
    }

    const w = (img.naturalWidth || 1920) * scale;
    const h = (img.naturalHeight || 1080) * scale;
    const x = (cw - w) / 2;
    const y = (ch - h) / 2;

    ctx.drawImage(img, x, y, w, h);
  }

  // Storytelling orchestrator synced with scroll
  function updateStory(progress) {
    // 1. Beginning: 0% to 20%
    if (introWrap) {
      if (progress <= 0.18) {
        const introOpacity = Math.max(0, 1 - (progress / 0.18));
        introWrap.style.opacity = introOpacity;
        if (window.innerWidth <= 768) {
          introWrap.style.transform = `translateY(-${progress * 35}px)`;
        } else {
          introWrap.style.transform = `translateY(calc(-50% - ${progress * 50}px))`;
        }
        introWrap.style.pointerEvents = introOpacity > 0.2 ? "auto" : "none";
      } else {
        introWrap.style.opacity = "0";
        introWrap.style.pointerEvents = "none";
      }
    }

    // Scroll Cue visibility (fade out early)
    if (scrollCue) {
      if (progress < 0.12) {
        scrollCue.style.opacity = String(Math.max(0, 1 - (progress / 0.10)));
      } else {
        scrollCue.style.opacity = "0";
      }
    }

    // Progress counter
    if (progressNum) {
      const displayFrame = String(Math.round(currentFrame) + 1).padStart(3, "0");
      progressNum.textContent = `${displayFrame} / ${frameCount}`;
    }

    // 2. Final: 80% to 100%
    if (outroWrap) {
      if (progress >= 0.78) {
        const outroProgress = Math.min(1, (progress - 0.78) / 0.18);
        outroWrap.style.opacity = String(outroProgress);
        outroWrap.style.transform = `translateX(-50%) translateY(${(1 - outroProgress) * 20}px)`;
        if (outroOverlay) {
          outroOverlay.style.opacity = String(outroProgress * 0.75);
        }
      } else {
        outroWrap.style.opacity = "0";
        if (outroOverlay) {
          outroOverlay.style.opacity = "0";
        }
      }
    }
  }

  // Animation render loop
  function render() {
    if (heroSection) {
      const heroRect = heroSection.getBoundingClientRect();
      const heroScrollHeight = heroSection.offsetHeight - window.innerHeight;
      if (heroScrollHeight > 0) {
        const scrolled = Math.max(0, -heroRect.top);
        const progress = Math.max(0, Math.min(1, scrolled / heroScrollHeight));
        targetFrame = progress * (frameCount - 1);
        updateStory(progress);
      }
    } else {
      const maxScroll = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
      const progress = Math.max(0, Math.min(1, window.scrollY / maxScroll));
      targetFrame = progress * (frameCount - 1);
      updateStory(progress);
    }

    // Smooth Lerp interpolation
    const diff = targetFrame - currentFrame;
    if (Math.abs(diff) < 0.005) {
      currentFrame = targetFrame;
    } else {
      currentFrame += diff * 0.14;
    }

    drawFrame(currentFrame);
    animationId = requestAnimationFrame(render);
  }

  // Main initializer
  async function init() {
    await fetchFrameList();
    images = new Array(frameCount);

    // 1. Immediately load Frame 0 as instant poster fallback
    const firstImg = await loadFrame(0);
    resize();
    if (firstImg) {
      drawFrame(0);
      if (bar) bar.style.width = "40%";
      if (percentEl) percentEl.textContent = "40%";
    }

    // 2. Fast pre-cache of initial 12 frames so scroll is silky from first touch
    const initialBatch = [];
    const preloadCount = Math.min(12, frameCount);
    for (let i = 1; i < preloadCount; i++) {
      initialBatch.push(
        loadFrame(i).then(() => {
          const pct = Math.min(95, Math.round(40 + (loadedCount / preloadCount) * 55));
          if (bar) bar.style.width = `${pct}%`;
          if (percentEl) percentEl.textContent = `${pct}%`;
        })
      );
    }

    // Dismiss loader quickly once initial batch is ready (or 600ms ceiling)
    const dismissLoader = () => {
      if (bar) bar.style.width = "100%";
      if (percentEl) percentEl.textContent = "100%";
      if (statusEl) statusEl.textContent = "AURELIS ATELIER READY";
      if (loader && !loader.classList.contains("done")) {
        loader.classList.add("done");
      }
      if (!isRunning) {
        isRunning = true;
        render();
      }
      // Stream remaining frames in background chunks
      streamRemainingFrames(preloadCount);
    };

    const fastTimeout = setTimeout(dismissLoader, 600);

    try {
      await Promise.all(initialBatch);
    } finally {
      clearTimeout(fastTimeout);
      dismissLoader();
    }
  }

  window.addEventListener("resize", resize, { passive: true });
  init();
})();

