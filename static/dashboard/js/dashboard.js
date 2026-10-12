(() => {
  const root = document.documentElement;

  // Mobile sidebar
  const sidebar = document.querySelector("#sidebar");
  const backdrop = document.querySelector(".sidebar-backdrop");
  const setSidebar = (open) => {
    if (!sidebar) return;
    sidebar.classList.toggle("open", open);
    backdrop?.classList.toggle("open", open);
  };
  document.querySelector("[data-sidebar-toggle]")?.addEventListener("click", () => setSidebar(!sidebar.classList.contains("open")));
  document.querySelector("[data-sidebar-close]")?.addEventListener("click", () => setSidebar(false));

  // Light / dark theme, remembered per browser
  document.querySelector("[data-theme-toggle]")?.addEventListener("click", () => {
    const current = root.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    const next = current === "dark" ? "light" : "dark";
    root.dataset.theme = next;
    try { localStorage.setItem("dash-theme", next); } catch (e) {}
  });

  // User dropdown
  document.querySelectorAll("[data-dropdown]").forEach((menu) => {
    const toggle = menu.querySelector("[data-dropdown-toggle]");
    toggle.addEventListener("click", (event) => {
      event.stopPropagation();
      const open = menu.classList.toggle("open");
      toggle.setAttribute("aria-expanded", String(open));
    });
  });
  document.addEventListener("click", () => {
    document.querySelectorAll("[data-dropdown].open").forEach((menu) => {
      menu.classList.remove("open");
      menu.querySelector("[data-dropdown-toggle]").setAttribute("aria-expanded", "false");
    });
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      setSidebar(false);
      document.body.click();
    }
  });

  // Tabs (opens the first tab that has an error after a failed save)
  document.querySelectorAll("[data-tabs]").forEach((tabs) => {
    const buttons = [...tabs.querySelectorAll("[data-tab]")];
    const show = (button) => {
      buttons.forEach((b) => {
        const active = b === button;
        b.classList.toggle("active", active);
        b.setAttribute("aria-selected", String(active));
        document.getElementById(b.dataset.tab)?.classList.toggle("active", active);
      });
    };
    buttons.forEach((b) => b.addEventListener("click", () => show(b)));
    const withError = buttons.find((b) => b.querySelector(".tab-error"));
    if (withError) show(withError);
  });

  // Image upload preview
  function wireImageInput(box) {
    if (!box) return;
    const input = box.querySelector("input[type=file]");
    const preview = box.querySelector(".image-preview");
    const name = box.querySelector(".file-name");
    input.addEventListener("change", () => {
      const file = input.files[0];
      if (!file) return;
      let img = preview.querySelector("img");
      if (!img) {
        img = document.createElement("img");
        img.alt = "";
        preview.prepend(img);
      }
      img.src = URL.createObjectURL(file);
      preview.classList.remove("empty");
      name.textContent = `${file.name} — will upload when you save`;
    });
  }
  document.querySelectorAll("[data-image-input]").forEach(wireImageInput);

  // Toasts
  const toastBox = () => {
    let box = document.querySelector(".toasts");
    if (!box) {
      box = document.createElement("div");
      box.className = "toasts";
      box.setAttribute("aria-live", "polite");
      document.querySelector(".content")?.prepend(box);
    }
    return box;
  };
  const wireToast = (toast) => {
    const close = () => {
      toast.classList.add("hide");
      setTimeout(() => toast.remove(), 300);
    };
    toast.querySelector("[data-toast-close]")?.addEventListener("click", close);
    if (!toast.classList.contains("toast-error")) setTimeout(close, 4500);
  };
  const showToast = (text, kind = "success") => {
    const toast = document.createElement("div");
    toast.className = `toast toast-${kind}`;
    toast.innerHTML = `<span class="icon">${kind === "error" ? "error" : "check_circle"}</span><span></span>
      <button type="button" class="toast-close" data-toast-close aria-label="Dismiss"><span class="icon">close</span></button>`;
    toast.children[1].textContent = text;
    toastBox().append(toast);
    wireToast(toast);
  };
  document.querySelectorAll("[data-toast]").forEach(wireToast);

  // CSRF token for fetch() calls
  const csrfToken = () =>
    document.querySelector("[name=csrfmiddlewaretoken]")?.value ||
    (document.cookie.match(/(?:^|; )csrftoken=([^;]+)/) || [])[1] || "";
  const postJSON = (url, body) =>
    fetch(url, {
      method: "POST",
      headers: { "X-CSRFToken": csrfToken(), Accept: "application/json", "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : null,
    }).then((r) => (r.ok ? r.json() : Promise.reject(r)));

  // Visibility toggle in lists
  document.querySelectorAll("[data-toggle-url]").forEach((button) => {
    button.addEventListener("click", async () => {
      button.disabled = true;
      try {
        const data = await postJSON(button.dataset.toggleUrl);
        button.classList.toggle("on", data.active);
        button.setAttribute("aria-checked", String(data.active));
        showToast(data.active ? "Now visible on the website." : "Hidden from the website.");
      } catch (e) {
        showToast("Could not update. Please reload and try again.", "error");
      } finally {
        button.disabled = false;
      }
    });
  });

  // Bulk selection
  document.querySelectorAll("[data-bulk-form]").forEach((form) => {
    const all = form.querySelector("[data-check-all]");
    const boxes = [...form.querySelectorAll("[data-check]")];
    const bar = form.querySelector("[data-bulk-bar]");
    const count = form.querySelector("[data-bulk-count]");
    const sync = () => {
      const n = boxes.filter((b) => b.checked).length;
      bar.hidden = n === 0;
      count.textContent = n;
      all.checked = n > 0 && n === boxes.length;
      all.indeterminate = n > 0 && n < boxes.length;
    };
    all?.addEventListener("change", () => {
      boxes.forEach((b) => (b.checked = all.checked));
      sync();
    });
    boxes.forEach((b) => b.addEventListener("change", sync));
  });

  // Confirm dangerous buttons
  document.querySelectorAll("[data-confirm]").forEach((el) => {
    el.addEventListener("click", (event) => {
      if (!confirm(el.dataset.confirm)) event.preventDefault();
    });
  });

  // Drag-and-drop ordering
  document.querySelectorAll("[data-sortable]").forEach((tbody) => {
    if (!window.Sortable) return;
    Sortable.create(tbody, {
      handle: ".drag-handle",
      animation: 150,
      onEnd: async () => {
        const ids = [...tbody.querySelectorAll("tr[data-id]")].map((tr) => tr.dataset.id);
        try {
          await postJSON(tbody.dataset.reorderUrl, { ids });
          showToast("Order saved.");
        } catch (e) {
          showToast("Could not save the new order.", "error");
        }
      },
    });
  });

  // Slug auto-fill (only while the slug field is empty or still auto-generated)
  const slugify = (text) =>
    text.toLowerCase().normalize("NFKD").replace(/[̀-ͯ]/g, "")
      .replace(/&/g, " and ").replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 50);
  document.querySelectorAll("[data-slug-from]").forEach((slug) => {
    const source = document.getElementById(slug.dataset.slugFrom);
    if (!source) return;
    let auto = !slug.value;
    slug.addEventListener("input", () => (auto = !slug.value));
    source.addEventListener("input", () => {
      if (auto) slug.value = slugify(source.value);
    });
  });

  // Rich text editors (Quill)
  document.querySelectorAll("[data-richtext]").forEach((box) => {
    if (!window.Quill) return;
    const textarea = box.querySelector("textarea");
    const holder = box.querySelector(".richtext-editor");
    textarea.classList.add("enhanced");
    holder.innerHTML = textarea.value;
    const uploadUrl = box.dataset.uploadUrl;
    const quill = new Quill(holder, {
      theme: "snow",
      placeholder: holder.dataset.placeholder,
      modules: {
        toolbar: {
          container: [
            [{ header: [2, 3, false] }],
            ["bold", "italic", "underline", "link"],
            [{ list: "ordered" }, { list: "bullet" }, "blockquote", "code-block"],
            uploadUrl ? ["image", "clean"] : ["clean"],
          ],
          handlers: {
            // Upload to the server instead of Quill's default base64-in-HTML.
            image() {
              const picker = document.createElement("input");
              picker.type = "file";
              picker.accept = "image/png,image/jpeg,image/gif,image/webp";
              picker.addEventListener("change", async () => {
                const file = picker.files[0];
                if (!file) return;
                const range = quill.getSelection(true);
                const data = new FormData();
                data.append("image", file);
                showToast("Uploading image…", "info");
                try {
                  const response = await fetch(uploadUrl, {
                    method: "POST",
                    headers: { "X-CSRFToken": csrfToken(), Accept: "application/json" },
                    body: data,
                  });
                  const result = await response.json();
                  if (!response.ok) throw new Error(result.error || "Upload failed.");
                  quill.insertEmbed(range.index, "image", result.url, "user");
                  quill.setSelection(range.index + 1, 0);
                  showToast("Image added.");
                } catch (error) {
                  showToast(error.message || "Upload failed.", "error");
                }
              });
              picker.click();
            },
          },
        },
      },
    });
    const sync = () => {
      textarea.value = quill.getText().trim() ? quill.getSemanticHTML() : "";
    };
    quill.on("text-change", () => {
      sync();
      textarea.dispatchEvent(new Event("input", { bubbles: true }));
    });
    textarea.form?.addEventListener("submit", sync);
  });

  // Add rows to an inline formset (e.g. project gallery)
  document.querySelectorAll("[data-formset]").forEach((section) => {
    const prefix = section.dataset.formset;
    const total = section.querySelector(`[name="${prefix}-TOTAL_FORMS"]`);
    const list = section.querySelector("[data-formset-list]");
    const template = section.querySelector("[data-formset-template]");
    section.querySelector("[data-formset-add]")?.addEventListener("click", () => {
      const index = Number(total.value);
      const html = template.innerHTML.replace(/__prefix__/g, String(index));
      list.insertAdjacentHTML("beforeend", html);
      total.value = index + 1;
      section.querySelector(".gallery-empty")?.setAttribute("hidden", "");
      const added = list.lastElementChild;
      wireImageInput(added.querySelector("[data-image-input]"));
      added.querySelector("input[type=file]")?.click();
    });
  });

  // Character counters for SEO and summary fields
  document.querySelectorAll("input[maxlength][name^='meta_']:not([name='meta_keywords']), textarea[maxlength][name^='meta_'], textarea[maxlength][name='excerpt']").forEach((input) => {
    const max = Number(input.maxLength);
    const counter = document.createElement("span");
    counter.className = "char-count";
    input.closest(".field")?.querySelector("label")?.append(counter);
    const update = () => {
      counter.textContent = `${input.value.length}/${max}`;
      counter.classList.toggle("near", input.value.length > max * 0.9);
    };
    input.addEventListener("input", update);
    update();
  });

  // Keyword chips: type a keyword and press Enter or comma; stored as "a, b, c" in the real input
  document.querySelectorAll("[data-keywords]").forEach((box) => {
    const source = box.querySelector("input");
    const max = Number(source.maxLength) || 255;
    source.type = "hidden";
    const chips = document.createElement("div");
    chips.className = "keyword-chips";
    const entry = document.createElement("input");
    entry.type = "text";
    entry.className = "keyword-entry";
    entry.placeholder = "Type a keyword, press Enter";
    entry.setAttribute("aria-label", "Add keyword");
    box.append(chips);
    chips.append(entry);

    let words = source.value.split(",").map((w) => w.trim()).filter(Boolean);
    const save = () => {
      source.value = words.join(", ");
      source.dispatchEvent(new Event("change", { bubbles: true }));
    };
    const render = () => {
      chips.querySelectorAll(".keyword-chip").forEach((c) => c.remove());
      words.forEach((word, i) => {
        const chip = document.createElement("span");
        chip.className = "keyword-chip";
        chip.textContent = word;
        const remove = document.createElement("button");
        remove.type = "button";
        remove.setAttribute("aria-label", `Remove ${word}`);
        remove.innerHTML = '<span class="icon">close</span>';
        remove.addEventListener("click", () => {
          words.splice(i, 1);
          save();
          render();
        });
        chip.append(remove);
        chips.insertBefore(chip, entry);
      });
    };
    const add = (text) => {
      let changed = false;
      text.split(",").map((w) => w.trim().replace(/\s+/g, " ")).filter(Boolean).forEach((word) => {
        if (words.some((w) => w.toLowerCase() === word.toLowerCase())) return;
        if ([...words, word].join(", ").length > max) {
          showToast(`Keywords are limited to ${max} characters in total.`, "error");
          return;
        }
        words.push(word);
        changed = true;
      });
      if (changed) {
        save();
        render();
      }
    };
    entry.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === ",") {
        event.preventDefault();
        add(entry.value);
        entry.value = "";
      } else if (event.key === "Backspace" && !entry.value && words.length) {
        words.pop();
        save();
        render();
      }
    });
    entry.addEventListener("paste", (event) => {
      event.preventDefault();
      add((event.clipboardData || window.clipboardData).getData("text"));
    });
    entry.addEventListener("blur", () => {
      add(entry.value);
      entry.value = "";
    });
    chips.addEventListener("click", (event) => {
      if (event.target === chips) entry.focus();
    });
    render();
  });

  // Live Google search-result preview under the SEO fields
  document.querySelectorAll("input[name='meta_description'], textarea[name='meta_description']").forEach((descInput) => {
    const form = descInput.form;
    const titleInput = form.querySelector("[name='meta_title']");
    if (!titleInput) return;
    const fallbackTitle = form.querySelector("[name='title'], [name='site_name']");
    const fallbackDesc = form.querySelector("[name='excerpt'], [name='short_description'], [name='summary']");
    const slugInput = form.querySelector("[name='slug']");
    const siteName = document.querySelector(".sidebar-brand strong")?.textContent.trim() || "";
    const path = form.dataset.seoPath || "";

    const preview = document.createElement("div");
    preview.className = "serp";
    preview.innerHTML = `<div class="serp-label">Google preview</div>
      <div class="serp-url"></div><div class="serp-title"></div><div class="serp-desc"></div>`;
    descInput.closest(".field").after(preview);

    const cut = (text, n) => (text.length > n ? text.slice(0, n - 1).trimEnd() + "…" : text);
    const update = () => {
      const own = titleInput.value.trim();
      const base = fallbackTitle?.value.trim();
      const title = own || (base && fallbackTitle.name === "title" ? `${base} | ${siteName}` : base) || siteName;
      const desc = descInput.value.trim() || fallbackDesc?.value.trim() || "Add an SEO description so Google shows a helpful summary here.";
      preview.querySelector(".serp-title").textContent = cut(title, 60);
      preview.querySelector(".serp-desc").textContent = cut(desc, 158);
      preview.querySelector(".serp-url").textContent =
        location.host + (path ? path.replace("__slug__", slugInput?.value || "…") : "/");
    };
    form.addEventListener("input", update);
    update();
  });

  // Auto-submit list filters
  document.querySelectorAll("[data-autosubmit]").forEach((select) => {
    select.addEventListener("change", () => select.form.submit());
  });

  // Warn before leaving a form with unsaved changes
  document.querySelectorAll("[data-unsaved-warning]").forEach((form) => {
    let dirty = false;
    form.addEventListener("input", () => (dirty = true));
    form.addEventListener("change", () => (dirty = true));
    form.addEventListener("submit", () => (dirty = false));
    window.addEventListener("beforeunload", (event) => {
      if (dirty) {
        event.preventDefault();
        event.returnValue = "";
      }
    });
  });
})();
