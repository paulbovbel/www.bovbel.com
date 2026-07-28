const cart = new Map();

const gallery = document.querySelector("[data-gallery]");
const summary = document.querySelector("[data-cart-summary]");
const checkout = document.querySelector("[data-checkout]");

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"]/g, (character) => {
    return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[character];
  });
}

function cartCount() {
  return Array.from(cart.values()).reduce((total, item) => total + item.quantity, 0);
}

function renderCart() {
  const count = cartCount();
  checkout.disabled = count === 0;
  checkout.textContent = "Checkout";

  if (count === 0) {
    summary.textContent = "No pieces selected.";
  } else {
    summary.textContent = count === 1 ? "1 piece selected." : `${count} pieces selected.`;
  }

  document.querySelectorAll("[data-variation-id]").forEach(updateItemControls);
}

function resetCheckout() {
  checkout.textContent = "Checkout";
  checkout.disabled = cartCount() === 0;
}

function itemCard(item) {
  const image = item.image_url
    ? `<img src="${escapeHtml(item.image_url)}" alt="${escapeHtml(item.name)}">`
    : '<div class="art-placeholder" aria-hidden="true"></div>';
  const imageFrame = item.buy_url
    ? `<a class="piece-image" href="${escapeHtml(item.buy_url)}">${image}</a>`
    : `<div class="piece-image">${image}</div>`;
  const description = item.description ? `<p>${escapeHtml(item.description)}</p>` : "";
  const price = item.price ? `<span class="price">${escapeHtml(item.price)}</span>` : "";
  const stock = Number(item.quantity_available ?? 0);
  const stockLabel = stock === 1 ? "1 available" : `${stock} available`;
  const soldOut = stock < 1 ? "disabled" : "";

  return `
    <article class="piece" data-variation-id="${escapeHtml(item.variation_id)}" data-title="${escapeHtml(item.name)}" data-price="${escapeHtml(item.price)}" data-stock="${stock}">
      ${imageFrame}
      <div class="piece-copy">
        <h2>${escapeHtml(item.name)}</h2>
        ${description}
        <div class="piece-actions">
          <span>${price}<span class="stock">${escapeHtml(stockLabel)}</span></span>
          <span class="selection-controls">
            <button type="button" data-select-decrease ${soldOut} aria-label="Decrease ${escapeHtml(item.name)} quantity">-</button>
            <span class="selected-count" data-selected-count>0</span>
            <button type="button" data-select-increase ${soldOut} aria-label="Increase ${escapeHtml(item.name)} quantity">+</button>
            <button type="button" data-select-remove ${soldOut} aria-label="Remove ${escapeHtml(item.name)} from selection">Remove</button>
          </span>
        </div>
      </div>
    </article>`;
}

function updateItemControls(piece) {
  const variationId = piece.dataset.variationId;
  const stock = Number(piece.dataset.stock || 0);
  const quantity = cart.get(variationId)?.quantity || 0;

  piece.querySelector("[data-selected-count]").textContent = String(quantity);
  piece.querySelector("[data-select-decrease]").disabled = quantity === 0;
  piece.querySelector("[data-select-increase]").disabled = stock === 0 || quantity >= stock;
  piece.querySelector("[data-select-remove]").disabled = quantity === 0;
}

function setItemQuantity(piece, quantity) {
  const variationId = piece.dataset.variationId;
  const stock = Number(piece.dataset.stock || 0);
  const nextQuantity = Math.max(0, Math.min(quantity, stock));

  if (nextQuantity === 0) {
    cart.delete(variationId);
  } else {
    cart.set(variationId, {
      title: piece.dataset.title,
      quantity: nextQuantity,
      stock,
    });
  }

  renderCart();
}

function bindSelectionControls() {
  gallery.addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button) {
      return;
    }

    const piece = button.closest("[data-variation-id]");
    if (!piece) {
      return;
    }

    const variationId = piece.dataset.variationId;
    const quantity = cart.get(variationId)?.quantity || 0;
    if (button.dataset.selectIncrease !== undefined) {
      setItemQuantity(piece, quantity + 1);
    } else if (button.dataset.selectDecrease !== undefined) {
      setItemQuantity(piece, quantity - 1);
    } else if (button.dataset.selectRemove !== undefined) {
      setItemQuantity(piece, 0);
    }
  });
}

async function loadCatalog() {
  try {
    const response = await fetch("/api/catalog");
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Unable to load available pieces");
    }
    if (!data.items?.length) {
      gallery.innerHTML = '<section class="empty-gallery" aria-label="Gallery"><p>Available pieces will appear here soon.</p></section>';
      return;
    }

    gallery.innerHTML = data.items.map(itemCard).join("");
    renderCart();
  } catch (error) {
    gallery.innerHTML = `<section class="empty-gallery" aria-label="Gallery error"><p>${escapeHtml(error.message)}</p></section>`;
  }
}

checkout?.addEventListener("click", async () => {
  checkout.disabled = true;
  checkout.textContent = "Opening...";

  try {
    const response = await fetch("/api/checkout", {
      method: "POST",
      headers: {"content-type": "application/json"},
      body: JSON.stringify({
        items: Array.from(cart.entries()).map(([variationId, item]) => ({
          variation_id: variationId,
          quantity: item.quantity,
        })),
      }),
    });
    const data = await response.json();

    if (!response.ok || !data.url) {
      throw new Error(data.error || "Unable to create checkout");
    }

    window.location.assign(data.url);
  } catch (error) {
    summary.textContent = error.message;
    checkout.disabled = false;
    checkout.textContent = "Checkout";
  }
});

window.addEventListener("pageshow", resetCheckout);

bindSelectionControls();
renderCart();
loadCatalog();
