/* Count published pages only. Preview and legacy hosts must not pollute totals.
   Pageviews go through the first-party relay at s.adaad.org, which forwards
   them to GoatCounter's count API with the visitor's IP and User-Agent.
   Tracker blocklists match gc.zgo.at and goatcounter.com, so the counter
   script is served from here (assets/tally.js, a copy of count.js) and the
   beacon never leaves adaad.org. Relay source: Adaad/site/analytics-relay. */
(function () {
  if (location.hostname !== 'aiwan.adaad.org') return;
  window.goatcounter = window.goatcounter || {};
  window.goatcounter.endpoint = 'https://s.adaad.org/v/j';
  var script = document.createElement('script');
  script.async = true;
  script.src = '/assets/tally.js';
  document.head.appendChild(script);
})();
