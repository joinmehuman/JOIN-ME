"use strict";

document.addEventListener("DOMContentLoaded", () => {
  const panelOrder = ["intro", "state", "view", "garden"];
  const panels = new Map(
    [...document.querySelectorAll("[data-panel]")].map((panel) => [panel.dataset.panel, panel])
  );
  const progressItems = [...document.querySelectorAll("[data-progress]")];
  const stateSummary = document.querySelector("#state-summary");
  const chosenView = document.querySelector("#chosen-view");
  const gardenStatus = document.querySelector("#garden-status");
  const controlStatus = document.querySelector("#control-status");
  const pond = document.querySelector("#pond");
  const motionToggle = document.querySelector("#motion-toggle");
  const soundToggle = document.querySelector("#sound-toggle");
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  const experience = {
    stateLabel: "",
    stateKey: "",
    viewText: "",
    viewIndex: 0,
    soundEnabled: false,
    audioContext: null,
    activeSources: new Set(),
    motionEnabled: !reducedMotion.matches,
    motionUserOverride: false,
  };

  const announce = (message) => {
    if (controlStatus) {
      controlStatus.textContent = message;
    }
  };

  const showPanel = (name) => {
    const activeIndex = panelOrder.indexOf(name);

    panels.forEach((panel, panelName) => {
      const isActive = panelName === name;
      panel.hidden = !isActive;
      panel.classList.toggle("is-active", isActive);
    });

    progressItems.forEach((item) => {
      const itemIndex = panelOrder.indexOf(item.dataset.progress);
      item.classList.toggle("is-current", itemIndex === activeIndex);
      item.classList.toggle("is-complete", itemIndex < activeIndex);
    });

    const activePanel = panels.get(name);
    const heading = activePanel ? activePanel.querySelector("h1, h2") : null;
    if (heading) {
      heading.setAttribute("tabindex", "-1");
      heading.focus({ preventScroll: true });
    }
    window.scrollTo({ top: 0, behavior: experience.motionEnabled ? "smooth" : "auto" });
  };

  const stopSources = () => {
    experience.activeSources.forEach((source) => {
      try {
        source.stop();
      } catch (_error) {
        // The source may already have ended. Nothing else is retained.
      }
    });
    experience.activeSources.clear();
  };

  const disableSound = () => {
    stopSources();
    if (experience.audioContext) {
      experience.audioContext.close().catch(() => {});
      experience.audioContext = null;
    }
    experience.soundEnabled = false;
    soundToggle.setAttribute("aria-pressed", "false");
    soundToggle.textContent = "音：オフ";
    announce("音を停止しました");
  };

  const playWaterTone = (viewIndex = 0) => {
    const context = experience.audioContext;
    if (!experience.soundEnabled || !context) {
      return;
    }

    if (context.state === "suspended") {
      context.resume().catch(() => {});
    }

    const toneSets = [
      [392.0, 523.25, 659.25],
      [349.23, 493.88, 587.33],
      [440.0, 554.37, 659.25],
    ];
    const now = context.currentTime;
    const master = context.createGain();
    master.gain.setValueAtTime(0.0001, now);
    master.gain.exponentialRampToValueAtTime(0.028, now + 0.05);
    master.gain.exponentialRampToValueAtTime(0.0001, now + 1.45);
    master.connect(context.destination);

    toneSets[viewIndex % toneSets.length].forEach((frequency, layerIndex) => {
      const source = context.createOscillator();
      const layerGain = context.createGain();
      source.type = layerIndex === 0 ? "sine" : "triangle";
      source.frequency.setValueAtTime(frequency, now);
      layerGain.gain.setValueAtTime(layerIndex === 0 ? 0.58 : 0.21, now);
      source.connect(layerGain);
      layerGain.connect(master);
      experience.activeSources.add(source);
      source.addEventListener("ended", () => experience.activeSources.delete(source), { once: true });
      source.start(now + layerIndex * 0.055);
      source.stop(now + 1.5);
    });
  };

  const enableSound = () => {
    const AudioEngine = window.AudioContext || window.webkitAudioContext;
    if (!AudioEngine) {
      soundToggle.textContent = "音：非対応";
      soundToggle.disabled = true;
      announce("このブラウザでは音を再生できません");
      return;
    }

    experience.audioContext = new AudioEngine();
    experience.soundEnabled = true;
    soundToggle.setAttribute("aria-pressed", "true");
    soundToggle.textContent = "音：オン";
    announce("音をオンにしました。音は操作したときだけ鳴ります");
    playWaterTone(experience.viewIndex);
  };

  const applyMotion = (enabled, userInitiated = false) => {
    experience.motionEnabled = enabled;
    if (userInitiated) {
      experience.motionUserOverride = true;
    }
    document.body.classList.toggle("motion-paused", !enabled);
    document.body.classList.toggle("motion-user-enabled", enabled && experience.motionUserOverride);
    motionToggle.setAttribute("aria-pressed", String(enabled));
    motionToggle.textContent = enabled ? "動き：オン" : "動き：停止";
    announce(enabled ? "動きをオンにしました" : "動きを停止しました");
  };

  document.querySelector("#start-button").addEventListener("click", () => showPanel("state"));

  document.querySelectorAll("[data-state]").forEach((button) => {
    button.addEventListener("click", () => {
      experience.stateLabel = button.dataset.state || "";
      experience.stateKey = button.dataset.stateKey || "";
      stateSummary.textContent = `選んだ天気：${experience.stateLabel}`;
      showPanel("view");
    });
  });

  document.querySelectorAll("[data-view-index]").forEach((button) => {
    button.addEventListener("click", () => {
      const viewText = button.querySelector(".view-text");
      experience.viewIndex = Number(button.dataset.viewIndex || 0);
      experience.viewText = viewText ? viewText.textContent.trim() : "";
      chosenView.textContent = experience.viewText;
      gardenStatus.textContent = "波紋は、水面に触れたときだけ広がります。";
      showPanel("garden");
    });
  });

  pond.addEventListener("click", () => {
    if (experience.motionEnabled) {
      pond.classList.remove("has-ripple");
      void pond.offsetWidth;
      pond.classList.add("has-ripple");
    }

    if (experience.soundEnabled) {
      playWaterTone(experience.viewIndex);
      gardenStatus.textContent = experience.motionEnabled
        ? "選んだ視点が、波紋と小さな音になりました。"
        : "選んだ視点が、小さな音になりました。動きは停止中です。";
    } else {
      gardenStatus.textContent = experience.motionEnabled
        ? "選んだ視点が、波紋になりました。音はオフです。"
        : "動きと音は停止中です。上の設定から個別に変更できます。";
    }
  });

  pond.addEventListener("animationend", () => pond.classList.remove("has-ripple"));

  motionToggle.addEventListener("click", () => applyMotion(!experience.motionEnabled, true));
  soundToggle.addEventListener("click", () => {
    if (experience.soundEnabled) {
      disableSound();
    } else {
      enableSound();
    }
  });

  reducedMotion.addEventListener("change", (event) => {
    if (!experience.motionUserOverride) {
      applyMotion(!event.matches);
    }
  });

  document.querySelector("#restart-button").addEventListener("click", () => {
    experience.stateLabel = "";
    experience.stateKey = "";
    experience.viewText = "";
    experience.viewIndex = 0;
    stateSummary.textContent = "";
    chosenView.textContent = "";
    gardenStatus.textContent = "波紋は、水面に触れたときだけ広がります。";
    pond.classList.remove("has-ripple");
    showPanel("intro");
  });

  window.addEventListener("pagehide", stopSources);
  applyMotion(!reducedMotion.matches);
});
