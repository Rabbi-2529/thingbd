const menuButton = document.querySelector(".menu-button");
const navigation = document.querySelector("#nav-links");

menuButton.addEventListener("click", () => {
  const open = navigation.classList.toggle("open");
  menuButton.setAttribute("aria-expanded", String(open));
});

navigation.addEventListener("click", () => {
  navigation.classList.remove("open");
  menuButton.setAttribute("aria-expanded", "false");
});

const form = document.querySelector("#lead-form");

if (form) {
  const status = form.querySelector(".form-status");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = form.querySelector("button[type='submit']");

    status.textContent = "Sending...";
    status.className = "form-status full";
    button.disabled = true;

    try {
      const response = await fetch(form.action, {
        method: "POST",
        headers: { Accept: "application/json" },
        body: new FormData(form),
      });
      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        const firstError = data.errors && Object.values(data.errors)[0];
        throw new Error((firstError && firstError[0]) || "Please check the form and try again.");
      }

      form.reset();
      status.textContent = "Thanks. We will contact you within one business day.";
      status.classList.add("success");
    } catch (error) {
      status.textContent = error.message;
      status.classList.add("error");
    } finally {
      button.disabled = false;
    }
  });
}
