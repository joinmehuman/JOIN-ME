/* =========================================================
   JOIN ME | Version 1
   script.js（完全版）
========================================================= */

document.addEventListener("DOMContentLoaded", () => {

  /* ==========================
     Hero Fade In
  ========================== */

  const hero = document.querySelector(".hero");

  if (hero) {
    hero.classList.add("show");
  }

  /* ==========================
     Scroll Animation
  ========================== */

  const sections = document.querySelectorAll(".fade-section");

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {

        if (entry.isIntersecting) {
          entry.target.classList.add("visible");
        }

      });
    },
    {
      threshold: 0.15,
    }
  );

  sections.forEach(section => observer.observe(section));

  /* ==========================
     Smooth Scroll
  ========================== */

  document.querySelectorAll('a[href^="#"]').forEach(anchor => {

    anchor.addEventListener("click", function (e) {

      e.preventDefault();

      const target = document.querySelector(this.getAttribute("href"));

      if (target) {

        target.scrollIntoView({
          behavior: "smooth",
          block: "start"
        });

      }

    });

  });

  /* ==========================
     CTA Button Effect
  ========================== */

  const buttons = document.querySelectorAll(".cta-button");

  buttons.forEach(button => {

    button.addEventListener("mouseenter", () => {
      button.style.transform = "translateY(-3px)";
    });

    button.addEventListener("mouseleave", () => {
      button.style.transform = "translateY(0)";
    });

  });

  /* ==========================
     Footer Year
  ========================== */

  const year = document.getElementById("year");

  if (year) {
    year.textContent = new Date().getFullYear();
  }

});
