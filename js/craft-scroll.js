/* ==========================================================================
   AURELIS — Discover Craft 3D Exploded Movement Video Engine
   Plays Video 2 (3D Exploded Caliber) smoothly at native 30/60fps without scroll lag.
   Synchronizes component callouts dynamically with playback progression.
   Allows smooth interactive clicking on callouts to jump between caliber stages.
   ========================================================================== */

(function () {
  const craftSection = document.getElementById("craft");
  const video = document.getElementById("craftVideo");
  if (!craftSection || !video) return;

  const craftProgressBar = document.getElementById("craftProgressBar");
  const calloutItems = document.querySelectorAll(".craft-callout-item");
  const scrubberInput = document.getElementById("craftScrubber");

  let isScrubbing = false;

  // Ensure video is properly configured for silent autoplay loop
  video.muted = true;
  video.loop = true;
  video.playsInline = true;
  video.setAttribute("muted", "");
  video.setAttribute("loop", "");
  video.setAttribute("playsinline", "");
  video.setAttribute("webkit-playsinline", "");

  // Safe playback helper
  function safePlay() {
    video.muted = true;
    video.playsInline = true;
    const p = video.play();
    if (p !== undefined) {
      p.catch(() => {
        const onFirstInteraction = () => {
          video.play().catch(() => {});
          window.removeEventListener("touchstart", onFirstInteraction);
          window.removeEventListener("click", onFirstInteraction);
          window.removeEventListener("scroll", onFirstInteraction);
        };
        window.addEventListener("touchstart", onFirstInteraction, { passive: true, once: true });
        window.addEventListener("click", onFirstInteraction, { passive: true, once: true });
        window.addEventListener("scroll", onFirstInteraction, { passive: true, once: true });
      });
    }
  }

  // Update active callout cards based on video time
  function updateCalloutsFromTime() {
    if (isScrubbing) return;
    const dur = video.duration || 8.0;
    const cur = video.currentTime;
    const p = dur > 0 ? Math.max(0, Math.min(1, cur / dur)) : 0;

    let activeStage = 0;
    if (p >= 0.85) activeStage = 4;
    else if (p >= 0.65) activeStage = 3;
    else if (p >= 0.40) activeStage = 2;
    else if (p >= 0.20) activeStage = 1;
    else activeStage = 0;

    calloutItems.forEach((item, idx) => {
      if (idx === activeStage) {
        item.classList.add("active");
      } else {
        item.classList.remove("active");
      }
    });

    if (craftProgressBar) {
      craftProgressBar.style.width = `${Math.round(p * 100)}%`;
    }

    if (scrubberInput && !isScrubbing) {
      scrubberInput.value = Math.round(p * 100);
    }
  }

  video.addEventListener("timeupdate", updateCalloutsFromTime, { passive: true });

  // Use IntersectionObserver: play smoothly when in view, pause when out of view
  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          safePlay();
        } else {
          video.pause();
        }
      });
    }, { threshold: 0.15 });

    observer.observe(craftSection);
  } else {
    safePlay();
  }

  // Interactive Callout Clicks: Clicking a stage jumps to that moment smoothly
  const stageTimings = [0.08, 0.28, 0.52, 0.74, 0.92]; // Fraction of total duration
  calloutItems.forEach((item, idx) => {
    item.addEventListener("click", () => {
      const dur = video.duration || 8.0;
      const targetTime = (stageTimings[idx] || 0) * dur;
      video.currentTime = targetTime;
      safePlay();

      calloutItems.forEach((c, i) => {
        if (i === idx) c.classList.add("active");
        else c.classList.remove("active");
      });
    });
  });

  // Interactive Scrubber controls
  if (scrubberInput) {
    scrubberInput.addEventListener("input", (e) => {
      isScrubbing = true;
      const val = parseFloat(e.target.value) / 100;
      const dur = video.duration || 8.0;
      video.currentTime = val * dur;
      if (craftProgressBar) {
        craftProgressBar.style.width = `${Math.round(val * 100)}%`;
      }
    });

    scrubberInput.addEventListener("change", () => {
      isScrubbing = false;
      safePlay();
    });
  }

  // Self-healing visibility check
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") {
      const rect = craftSection.getBoundingClientRect();
      if (rect.top < window.innerHeight && rect.bottom > 0) {
        safePlay();
      }
    }
  });

  // Initial playback attempt
  safePlay();
})();
