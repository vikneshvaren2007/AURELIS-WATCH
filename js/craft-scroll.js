/* ==========================================================================
   AURELIS — Interactive 3D Exploded Horology Craft Scrollytelling Engine
   Dedicated to Frame 2 (240 frames: ezgif-frame-001.jpg to ezgif-frame-240.jpg)
   Provides bidirectional smooth scroll kinematics, high-DPI canvas rendering,
   component HUD callouts, and manual scrubber controls.
   ========================================================================== */

(function () {
  const craftSection = document.getElementById("craft");
  const canvas = document.getElementById("craftCanvas");
  if (!craftSection || !canvas) return;

  const ctx = canvas.getContext("2d", { alpha: false, desynchronized: true });
  const frameCountDisplay = document.getElementById("craftFrameNum");
  const craftProgressBar = document.getElementById("craftProgressBar");
  const calloutItems = document.querySelectorAll(".craft-callout-item");
  const scrubberInput = document.getElementById("craftScrubber");

  const TOTAL_FRAMES = 240;
  let craftFrames = [];
  let images = new Array(TOTAL_FRAMES);
  let currentFrame = 0;
  let targetFrame = 0;
  let isLoaded = false;
  let animationFrameId = null;
  let isScrubbing = false;

  // Build frame URLs with properly encoded spaces
  for (let i = 1; i <= TOTAL_FRAMES; i++) {
    const padded = String(i).padStart(3, "0");
    craftFrames.push(`./frames%202/ezgif-frame-${padded}.jpg`);
  }

  // Preload a single frame
  function loadFrame(index) {
    return new Promise((resolve) => {
      if (images[index]) return resolve(images[index]);
      const img = new Image();
      img.decoding = "async";
      img.src = craftFrames[index];
      img.onload = () => {
        images[index] = img;
        resolve(img);
      };
      img.onerror = () => {
        // Fallback without URL encoding
        const unencoded = craftFrames[index].replace("%20", " ");
        if (img.src !== unencoded) {
          img.src = unencoded;
        } else {
          resolve(null);
        }
      };
    });
  }

  // Progressive background streaming of remaining craft frames
  async function streamCraftFrames() {
    const batchSize = 6;
    for (let i = 25; i < TOTAL_FRAMES; i += batchSize) {
      const batch = [];
      for (let j = 0; j < batchSize && (i + j) < TOTAL_FRAMES; j++) {
        batch.push(loadFrame(i + j));
      }
      await Promise.all(batch);
      await new Promise((r) => setTimeout(r, 20));
    }
  }

  // High-DPI responsive canvas sizing
  function resize() {
    const rect = canvas.getBoundingClientRect();
    const w = rect.width || window.innerWidth;
    const h = rect.height || window.innerHeight;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    drawFrame(currentFrame);
  }

  // Draw frame with pristine aspect ratio preservation
  function drawFrame(index) {
    const safeIndex = Math.max(0, Math.min(TOTAL_FRAMES - 1, Math.round(index)));
    let img = images[safeIndex];

    // Find nearest neighbor if current frame is loading
    if (!img) {
      for (let offset = 1; offset < 25; offset++) {
        if (images[safeIndex - offset]) { img = images[safeIndex - offset]; break; }
        if (images[safeIndex + offset]) { img = images[safeIndex + offset]; break; }
      }
    }
    if (!img) img = images[0];
    if (!img) return;

    const rect = canvas.getBoundingClientRect();
    const cw = rect.width || window.innerWidth;
    const ch = rect.height || window.innerHeight;

    // Deep luxury atelier background fill (#080706)
    ctx.fillStyle = "#080706";
    ctx.fillRect(0, 0, cw, ch);

    const naturalW = img.naturalWidth || 1920;
    const naturalH = img.naturalHeight || 1080;
    const imgAspect = naturalW / naturalH;
    const canvasAspect = cw / ch;

    let drawW, drawH;
    if (canvasAspect > imgAspect) {
      // Fit height
      drawH = ch * 0.95;
      drawW = drawH * imgAspect;
    } else {
      // Fit width
      drawW = cw * 0.95;
      drawH = drawW / imgAspect;
    }

    const x = (cw - drawW) / 2;
    const y = (ch - drawH) / 2;

    ctx.drawImage(img, x, y, drawW, drawH);
  }

  // Update component HUD callouts based on disassembly progression
  function updateCallouts(progress) {
    // 5 Stages of Explosion
    // Stage 1: 0.00 - 0.20 -> Bezel & Crystal
    // Stage 2: 0.20 - 0.40 -> Guilloché Dial & Hands
    // Stage 3: 0.40 - 0.65 -> Caliber Escapement & Rotor
    // Stage 4: 0.65 - 0.85 -> Surgical Steel Case & Crown
    // Stage 5: 0.85 - 1.00 -> Exhibition Back & Solid Bracelet

    let activeStage = 0;
    if (progress >= 0.85) activeStage = 4;
    else if (progress >= 0.65) activeStage = 3;
    else if (progress >= 0.40) activeStage = 2;
    else if (progress >= 0.18) activeStage = 1;
    else activeStage = 0;

    calloutItems.forEach((item, idx) => {
      if (idx === activeStage) {
        item.classList.add("active");
      } else {
        item.classList.remove("active");
      }
    });

    if (frameCountDisplay) {
      const displayFrame = String(Math.round(currentFrame) + 1).padStart(3, "0");
      frameCountDisplay.textContent = `EXPLODED FRAME ${displayFrame} / ${TOTAL_FRAMES}`;
    }

    if (craftProgressBar) {
      craftProgressBar.style.width = `${Math.round(progress * 100)}%`;
    }

    if (scrubberInput && !isScrubbing) {
      scrubberInput.value = Math.round(progress * 100);
    }
  }

  // Main scroll kinematics update
  function updateScroll() {
    if (isScrubbing) return;
    const rect = craftSection.getBoundingClientRect();
    const scrollDistance = craftSection.offsetHeight - window.innerHeight;
    if (scrollDistance <= 0) return;

    // Viewport-relative scrolled depth
    const scrolled = -rect.top;
    const progress = Math.max(0, Math.min(1, scrolled / scrollDistance));

    targetFrame = progress * (TOTAL_FRAMES - 1);
  }

  // Render loop with smooth lerp kinematics
  function render() {
    const diff = targetFrame - currentFrame;
    if (Math.abs(diff) < 0.008) {
      currentFrame = targetFrame;
    } else {
      currentFrame += diff * 0.16;
    }

    const progress = currentFrame / (TOTAL_FRAMES - 1);
    drawFrame(currentFrame);
    updateCallouts(progress);

    animationFrameId = requestAnimationFrame(render);
  }

  // Setup interactive callout clicks (jump to component explosion point)
  function setupCalloutClicks() {
    const targetProgressPoints = [0.10, 0.30, 0.52, 0.75, 0.95];
    calloutItems.forEach((item, idx) => {
      item.addEventListener("click", () => {
        const p = targetProgressPoints[idx] || 0;
        const scrollDistance = craftSection.offsetHeight - window.innerHeight;
        const targetScrollY = craftSection.offsetTop + (p * scrollDistance);
        window.scrollTo({ top: targetScrollY, behavior: "smooth" });
      });
    });

    if (scrubberInput) {
      scrubberInput.addEventListener("input", (e) => {
        isScrubbing = true;
        const p = parseFloat(e.target.value) / 100;
        targetFrame = p * (TOTAL_FRAMES - 1);
      });

      scrubberInput.addEventListener("change", (e) => {
        const p = parseFloat(e.target.value) / 100;
        const scrollDistance = craftSection.offsetHeight - window.innerHeight;
        const targetScrollY = craftSection.offsetTop + (p * scrollDistance);
        window.scrollTo({ top: targetScrollY, behavior: "auto" });
        isScrubbing = false;
      });
    }
  }

  // Initialization
  async function init() {
    // 1. Immediately load first frame
    const firstImg = await loadFrame(0);
    resize();
    if (firstImg) {
      drawFrame(0);
    }

    // 2. Pre-cache initial 25 frames
    const initialBatch = [];
    for (let i = 1; i < 25; i++) {
      initialBatch.push(loadFrame(i));
    }
    await Promise.all(initialBatch);
    isLoaded = true;

    // 3. Start render loop
    render();

    // 4. Stream rest in background
    streamCraftFrames();

    // 5. Wire click & scrub interactions
    setupCalloutClicks();
  }

  window.addEventListener("scroll", updateScroll, { passive: true });
  window.addEventListener("resize", resize, { passive: true });

  // Boot craft engine
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
