/* ==========================================================================
   AURELIS — Haute Horlogerie Cinematic Hero Video Controller (Single Video)
   Plays Video 1 (Chronograph Assembly) smoothly on continuous loop.
   Zero alternating video in hero. Video 2 resides exclusively in Discover Craft.
   ========================================================================== */

(function () {
  const v1 = document.getElementById("heroVideo1");
  const poster = document.getElementById("heroPosterFallback");

  const loader = document.getElementById("loader");
  const bar = document.getElementById("loaderBar");
  const percentEl = document.getElementById("loaderPercent");
  const statusEl = document.getElementById("loaderStatus");
  const nav = document.getElementById("mainNav");
  const introWrap = document.getElementById("heroIntro");
  const outroWrap = document.getElementById("heroOutro");
  const outroOverlay = document.getElementById("heroOutroOverlay");
  const scrollCue = document.getElementById("heroScrollCue");
  const heroSection = document.getElementById("hero");

  if (!v1) return;

  let isLoaderDismissed = false;

  // Ensure video 1 is muted, looped, and playsinline
  v1.muted = true;
  v1.loop = true;
  v1.playsInline = true;
  v1.setAttribute("muted", "");
  v1.setAttribute("loop", "");
  v1.setAttribute("playsinline", "");
  v1.setAttribute("webkit-playsinline", "");

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

  // Bulletproof autoplay handler adhering strictly to browser autoplay policies
  function safePlay(video) {
    if (!video) return Promise.resolve();
    video.muted = true;
    video.loop = true;
    video.playsInline = true;
    video.setAttribute("muted", "");
    video.setAttribute("loop", "");
    video.setAttribute("playsinline", "");
    video.setAttribute("webkit-playsinline", "");

    const p = video.play();
    if (p !== undefined) {
      return p.catch((err) => {
        console.warn("[AURELIS Hero] Autoplay restricted, will resume on interaction", err);
        const resumeOnGesture = () => {
          video.play().catch(() => {});
          window.removeEventListener("touchstart", resumeOnGesture);
          window.removeEventListener("click", resumeOnGesture);
          window.removeEventListener("scroll", resumeOnGesture);
        };
        window.addEventListener("touchstart", resumeOnGesture, { passive: true, once: true });
        window.addEventListener("click", resumeOnGesture, { passive: true, once: true });
        window.addEventListener("scroll", resumeOnGesture, { passive: true, once: true });
      });
    }
    return Promise.resolve();
  }

  // Dismiss loader once hero video is ready
  function dismissLoader() {
    if (isLoaderDismissed) return;
    isLoaderDismissed = true;
    if (bar) bar.style.width = "100%";
    if (percentEl) percentEl.textContent = "100%";
    if (statusEl) statusEl.textContent = "AURELIS ATELIER READY";
    if (loader) {
      loader.classList.add("done");
    }
    if (poster) {
      setTimeout(() => poster.classList.add("hidden"), 300);
    }
    safePlay(v1);
  }

  // Scroll kinematics for hero intro copy and outro statement
  function updateScroll() {
    if (!heroSection) return;
    const heroRect = heroSection.getBoundingClientRect();
    const heroScrollHeight = heroSection.offsetHeight - window.innerHeight;
    if (heroScrollHeight <= 0) {
      if (introWrap) {
        introWrap.style.opacity = "1";
        introWrap.style.pointerEvents = "auto";
      }
      return;
    }


    const scrolled = Math.max(0, -heroRect.top);
    const progress = Math.max(0, Math.min(1, scrolled / heroScrollHeight));

    // 1. Intro Copy (0% - 18%)
    if (introWrap) {
      if (progress <= 0.18) {
        const introOpacity = Math.max(0, 1 - (progress / 0.18));
        introWrap.style.opacity = String(introOpacity);
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

    // 2. Scroll Cue (fade out early)
    if (scrollCue) {
      if (progress < 0.12) {
        scrollCue.style.opacity = String(Math.max(0, 1 - (progress / 0.10)));
      } else {
        scrollCue.style.opacity = "0";
      }
    }

    // 3. Outro Statement (78% - 100%)
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

  window.addEventListener("scroll", updateScroll, { passive: true });

  // Event listeners for hero video 1
  v1.addEventListener("loadeddata", dismissLoader);
  v1.addEventListener("canplay", dismissLoader);
  v1.addEventListener("ended", () => {
    v1.currentTime = 0;
    safePlay(v1);
  });

  // Watchdog timer: Dismiss loader within 350ms max
  setTimeout(dismissLoader, 350);

  // Self-healing watchdog: resume if tab regains focus
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible" && v1) {
      if (v1.paused) safePlay(v1);
    }
  });

  // Periodic heartbeat: guarantees continuous smooth loop
  setInterval(() => {
    if (v1 && v1.paused && document.visibilityState === "visible") {
      safePlay(v1);
    }
  }, 2000);

  // Initial play call
  safePlay(v1);
})();
