/* 나비 날개 AR — 서비스 워커
   교실 와이파이가 느리거나 끊겨도 두 번째부터는 바로 열리게 합니다.

   - 우리 파일(HTML·JSON·아이콘): 네트워크 먼저, 4초 안에 응답이 없거나 실패하면 캐시.
     → 새로 배포하면 바로 반영되고, 오프라인에서도 열립니다.
   - 포즈 모델과 라이브러리(주소에 버전이 박혀 있어 내용이 바뀌지 않음): 캐시 먼저.
     → 한 번 받으면 다시 내려받지 않습니다 (약 3 MB 절약).
*/

const VER   = "bw-2026-09-23";
const SHELL = "shell-" + VER;
const FAR   = "far-" + VER;          // 멀리 있는, 변하지 않는 파일

const PRECACHE = [
  "./",
  "./index.html",
  "./butterflies.json",
  "./manifest.webmanifest",
  "./icon-180.png",
  "./icon-192.png",
  "./icon-512.png",
  "./icon-maskable-512.png"
];

/* 버전이 주소에 박혀 있어 한 번 받으면 바뀌지 않는 것들 */
const isFar = url =>
  url.hostname === "cdn.jsdelivr.net" ||
  (url.hostname === "storage.googleapis.com" && url.pathname.startsWith("/mediapipe-models/"));

self.addEventListener("install", e => {
  e.waitUntil(
    caches.open(SHELL)
      .then(c => c.addAll(PRECACHE))
      .catch(() => {})          // 한 파일이 실패해도 설치는 진행
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(
        keys.filter(k => k !== SHELL && k !== FAR).map(k => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

/* 캐시를 찾을 때는 ?v=123 같은 꼬리표를 떼고 봅니다 */
const keyFor = req => {
  const u = new URL(req.url);
  u.search = "";
  return u.href;
};

async function networkFirst(req){
  const cache = await caches.open(SHELL);
  const net = fetch(req).then(r => {
    if (r && r.ok) cache.put(keyFor(req), r.clone());
    return r;
  });
  net.catch(() => {});      // 캐시로 답한 뒤 늦게 실패해도 조용히
  const slow = new Promise(r => setTimeout(() => r("slow"), 4000));
  let first;
  try { first = await Promise.race([net, slow]); }
  catch (err){                                  // 네트워크가 바로 실패
    const hit = await cache.match(keyFor(req), { ignoreVary: true });
    if (hit) return hit;
    throw err;
  }
  if (first !== "slow") return first;

  // 4초가 지났다 — 캐시가 있으면 먼저 보여주고, 없으면 네트워크를 계속 기다립니다
  const hit = await cache.match(keyFor(req), { ignoreVary: true });
  if (hit) return hit;
  return net;
}

async function cacheFirst(req){
  const cache = await caches.open(FAR);
  const hit = await cache.match(keyFor(req), { ignoreVary: true });
  if (hit) return hit;
  const net = await fetch(req);
  if (net && net.ok) cache.put(keyFor(req), net.clone());
  return net;
}

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);

  if (url.origin === self.location.origin){
    e.respondWith(networkFirst(req));
  } else if (isFar(url)){
    e.respondWith(cacheFirst(req));
  }
  // 그 밖의 요청은 건드리지 않습니다
});
