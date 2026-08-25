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
  const plusSampleButton = document.querySelector("#plus-sample-button");
  const plusStatus = document.querySelector("#plus-status");
  const soundForest = document.querySelector("#sound-forest");
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  const experience = {
    stateLabel: "",
    stateKey: "",
    viewText: "",
    viewIndex: 0,
    soundEnabled: false,
    audioContext: null,
    activeSources: new Set(),
    plusUsed: false,
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
    soundToggle.textContent = "音を試す";
    announce("音を停止しました");
  };

  const prepareAudio = async () => {
    const AudioEngine = window.AudioContext || window.webkitAudioContext;
    if (!AudioEngine) {
      soundToggle.textContent = "音：非対応";
      soundToggle.disabled = true;
      announce("このブラウザでは音を再生できません");
      return false;
    }

    if (!experience.audioContext || experience.audioContext.state === "closed") {
      try {
        experience.audioContext = new AudioEngine({ latencyHint: "interactive" });
      } catch (_error) {
        experience.audioContext = new AudioEngine();
      }
    }

    const context = experience.audioContext;
    const unlockSource = context.createOscillator();
    const unlockGain = context.createGain();
    unlockGain.gain.setValueAtTime(0.0001, context.currentTime);
    unlockSource.connect(unlockGain);
    unlockGain.connect(context.destination);
    unlockSource.start(context.currentTime);
    unlockSource.stop(context.currentTime + 0.015);

    try {
      await context.resume();
    } catch (_error) {
      announce("音を開始できませんでした。もう一度、音を試すを押してください");
      return false;
    }

    if (context.state !== "running") {
      announce("音声が待機中です。iPhoneの音量を確認し、もう一度押してください");
      return false;
    }

    experience.soundEnabled = true;
    soundToggle.setAttribute("aria-pressed", "true");
    soundToggle.textContent = "音：停止";
    return true;
  };

  const playLayers = async (frequencies, durationSeconds = 1.25) => {
    const context = experience.audioContext;
    if (!experience.soundEnabled || !context) {
      return false;
    }

    if (context.state !== "running") {
      try {
        await context.resume();
      } catch (_error) {
        return false;
      }
    }

    if (context.state !== "running") {
      return false;
    }

    const now = context.currentTime;
    const master = context.createGain();
    const limiter = context.createDynamicsCompressor();
    limiter.threshold.setValueAtTime(-24, now);
    limiter.knee.setValueAtTime(18, now);
    limiter.ratio.setValueAtTime(10, now);
    limiter.attack.setValueAtTime(0.003, now);
    limiter.release.setValueAtTime(0.22, now);
    master.gain.setValueAtTime(0.0001, now);
    master.gain.exponentialRampToValueAtTime(0.13, now + 0.045);
    master.gain.exponentialRampToValueAtTime(0.0001, now + durationSeconds);
    master.connect(limiter);
    limiter.connect(context.destination);

    frequencies.slice(0, 3).forEach((frequency, layerIndex) => {
      const source = context.createOscillator();
      const layerGain = context.createGain();
      source.type = "sine";
      source.frequency.setValueAtTime(frequency, now);
      layerGain.gain.setValueAtTime([0.62, 0.2, 0.14][layerIndex] || 0.14, now);
      source.connect(layerGain);
      layerGain.connect(master);
      experience.activeSources.add(source);
      source.addEventListener("ended", () => experience.activeSources.delete(source), { once: true });
      source.start(now + layerIndex * 0.08);
      source.stop(now + durationSeconds + 0.05);
    });
    return true;
  };

  const playWaterTone = async (viewIndex = 0) => {
    const basicTones = [523.25, 587.33, 659.25];
    return playLayers([basicTones[viewIndex % basicTones.length]], 1.05);
  };

  const playSoundForest = async () => {
    const forestToneSets = [
      [523.25, 659.25, 783.99],
      [493.88, 587.33, 739.99],
      [440.0, 554.37, 698.46],
    ];
    return playLayers(forestToneSets[experience.viewIndex % forestToneSets.length], 2.4);
  };

  const enableSound = async (playConfirmation = true) => {
    const ready = await prepareAudio();
    if (!ready) {
      return false;
    }

    announce("音を開始しました。停止は上の音ボタンです");
    if (playConfirmation) {
      await playWaterTone(experience.viewIndex);
    }
    return true;
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

  pond.addEventListener("click", async () => {
    if (experience.motionEnabled) {
      pond.classList.remove("has-ripple");
      void pond.offsetWidth;
      pond.classList.add("has-ripple");
    }

    if (experience.soundEnabled) {
      const played = await playWaterTone(experience.viewIndex);
      if (played) {
        gardenStatus.textContent = experience.motionEnabled
          ? "選んだ視点が、波紋と1つの水音になりました。"
          : "選んだ視点が、1つの水音になりました。動きは停止中です。";
      } else {
        gardenStatus.textContent = "音を再開できませんでした。上の「音を試す」を押してください。";
        disableSound();
      }
    } else {
      gardenStatus.textContent = experience.motionEnabled
        ? "選んだ視点が、波紋になりました。音はオフです。"
        : "動きと音は停止中です。上の設定から個別に変更できます。";
    }
  });

  pond.addEventListener("animationend", () => pond.classList.remove("has-ripple"));

  motionToggle.addEventListener("click", () => applyMotion(!experience.motionEnabled, true));
  soundToggle.addEventListener("click", async () => {
    if (experience.soundEnabled) {
      disableSound();
    } else {
      soundToggle.disabled = true;
      await enableSound(true);
      if (soundToggle.textContent !== "音：非対応") {
        soundToggle.disabled = false;
      }
    }
  });

  plusSampleButton.addEventListener("click", async () => {
    if (experience.plusUsed) {
      return;
    }

    plusSampleButton.disabled = true;
    plusSampleButton.textContent = "音を準備しています…";
    plusStatus.textContent = "iPhoneの音量を確認してください。";

    const ready = experience.soundEnabled ? true : await enableSound(false);
    if (!ready) {
      plusSampleButton.disabled = false;
      plusSampleButton.textContent = "Plus「音の森」をもう一度試す";
      plusStatus.textContent = "音を開始できませんでした。iPhoneの音量を上げて、もう一度押してください。";
      return;
    }

    const played = await playSoundForest();
    if (!played) {
      plusSampleButton.disabled = false;
      plusSampleButton.textContent = "Plus「音の森」をもう一度試す";
      plusStatus.textContent = "音を再生できませんでした。上の音ボタンを押してから再度お試しください。";
      return;
    }

    experience.plusUsed = true;
    plusSampleButton.textContent = "Plus「音の森」体験済み";
    plusStatus.textContent = "3層の音と光が重なりました。この体験中のPlus見本は終了です。";
    if (experience.motionEnabled) {
      soundForest.classList.remove("is-playing");
      void soundForest.offsetWidth;
      soundForest.classList.add("is-playing");
      window.setTimeout(() => soundForest.classList.remove("is-playing"), 3100);
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
