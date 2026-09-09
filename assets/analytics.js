/* Count published pages only. Preview and legacy hosts must not pollute totals. */
(function () {
  if (location.hostname !== 'aiwan.adaad.org') return;
  window.goatcounter = window.goatcounter || {};
  var script = document.createElement('script');
  script.async = true;
  script.src = 'https://gc.zgo.at/count.js';
  script.setAttribute('data-goatcounter', 'https://aiwan.goatcounter.com/count');
  document.head.appendChild(script);
})();
