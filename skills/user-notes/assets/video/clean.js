(() => {
  const PRIVATE = /(@[a-z0-9.-]+\.[a-z]{2,})|(^\s*Locked by\b)|(\b(Limited|LLC|Ltd|Inc|Corp|Group|Industrial|Manufactur\w*|Trading)\b)/;
  const NOISE = /test environment|sandbox writes|did not load/i;
  const blur = el => {
    if (el.dataset.unBlur) return;
    el.dataset.unBlur = '1';
    el.style.filter = 'blur(6px)';
  };
  const clean = () => {
    document.querySelectorAll('nextjs-portal').forEach(el => { el.style.display = 'none'; });
    document.querySelectorAll('[role="alert"], [role="status"], [role="banner"], [class*="banner"], [class*="bg-orange"]').forEach(el => {
      if (NOISE.test(el.textContent || '')) el.style.display = 'none';
    });
    if (!document.body) return;
    document.querySelectorAll('input, textarea').forEach(el => { if (PRIVATE.test(el.value || '')) blur(el); });
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      if (node.parentElement && PRIVATE.test(node.nodeValue || '')) blur(node.parentElement);
    }
  };
  new MutationObserver(clean).observe(document, { childList: true, subtree: true, characterData: true });
  document.addEventListener('DOMContentLoaded', clean);
  document.addEventListener('input', clean, true);
})();
