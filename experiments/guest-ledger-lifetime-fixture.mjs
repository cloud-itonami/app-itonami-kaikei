// JUN-771 synthetic-only storage-port lifetime experiment. This does not
// authenticate a guest or qualify a product host. Mutation observation is
// asynchronous and cannot reverse a transaction that already committed.
export function watchFixtureGuest(frame, container, bridge) {
  const doc = container?.ownerDocument;
  if (!frame || !container?.isConnected || frame.parentNode !== container
      || !frame.isConnected || !doc || typeof MutationObserver !== 'function'
      || typeof bridge?.close !== 'function') throw new TypeError('connected fixture guest required');
  let closed = false, loaded = false;
  const observer = new MutationObserver(records => {
    if (!frame.isConnected || frame.parentNode !== container || records.some(({removedNodes}) =>
      Array.from(removedNodes).some(node => node === frame || node.contains?.(frame)))) close();
  });
  function close() {
    if (closed) return;
    closed = true;
    observer.disconnect();
    frame.removeEventListener('load', onLoad);
    bridge.close();
  }
  function onLoad() { if (loaded) close(); else loaded = true; }
  frame.addEventListener('load', onLoad);
  observer.observe(doc, {childList:true, subtree:true});
  return Object.freeze({close});
}
