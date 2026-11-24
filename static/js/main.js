// Skill Swap Management System - Main JavaScript

document.addEventListener("DOMContentLoaded", function () {
  // 1. Auto-dismiss alerts after 5 seconds
  const alerts = document.querySelectorAll(".alert-dismissible");
  alerts.forEach(function (alert) {
    setTimeout(function () {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) {
        bsAlert.close();
      }
    }, 5000);
  });

  // 2. Generic confirmation dialogs
  document.querySelectorAll("[data-confirm]").forEach(function (element) {
    element.addEventListener("click", function (e) {
      const message = this.getAttribute("data-confirm") || "Are you sure you want to proceed?";
      if (!confirm(message)) {
        e.preventDefault();
      }
    });
  });

  // 3. Dynamic Category -> Skill Filter on My Skills Modal
  const categorySelect = document.getElementById("modal_category_select");
  const skillSelect = document.getElementById("modal_skill_select");
  if (categorySelect && skillSelect) {
    categorySelect.addEventListener("change", function () {
      const selectedCategory = this.value;
      const options = skillSelect.querySelectorAll("option[data-category]");
      let firstVisible = null;

      options.forEach(function (opt) {
        if (!selectedCategory || opt.getAttribute("data-category") === selectedCategory) {
          opt.style.display = "";
          if (!firstVisible) firstVisible = opt.value;
        } else {
          opt.style.display = "none";
        }
      });

      if (firstVisible) {
        skillSelect.value = firstVisible;
      }
    });
  }

  // 4. Interactive Feedback Star Rating Picker
  const starContainers = document.querySelectorAll(".interactive-stars");
  starContainers.forEach(function (container) {
    const input = container.querySelector("input[type='hidden']");
    const stars = container.querySelectorAll(".bi-star, .bi-star-fill");

    stars.forEach(function (star, idx) {
      star.style.cursor = "pointer";
      star.addEventListener("click", function () {
        const rating = idx + 1;
        if (input) input.value = rating;
        updateStars(container, rating);
      });

      star.addEventListener("mouseenter", function () {
        updateStars(container, idx + 1);
      });
    });

    container.addEventListener("mouseleave", function () {
      const currentVal = input ? parseInt(input.value || "5") : 5;
      updateStars(container, currentVal);
    });
  });

  function updateStars(container, rating) {
    const stars = container.querySelectorAll(".bi-star, .bi-star-fill");
    stars.forEach(function (star, idx) {
      if (idx < rating) {
        star.classList.remove("bi-star");
        star.classList.add("bi-star-fill");
      } else {
        star.classList.remove("bi-star-fill");
        star.classList.add("bi-star");
      }
    });
  }
});
