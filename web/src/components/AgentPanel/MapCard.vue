<template>
  <div class="map-card">
    <div class="map-header">
      <span class="map-title">📍 {{ title }}</span>
      <span class="map-badge">{{ markers.length }} 个位置</span>
    </div>
    <div ref="containerRef" class="map-body">
      <div class="map-zoom-controls">
        <button class="map-zoom-btn" title="放大" @click.stop="zoomIn">
          <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M8 3.5v9M3.5 8h9" />
          </svg>
        </button>
        <span class="map-zoom-divider"></span>
        <button class="map-zoom-btn" title="缩小" @click.stop="zoomOut">
          <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3.5 8h9" />
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from "vue";
import AMapLoader from "@amap/amap-jsapi-loader";

interface MapMarker {
  lat: number;
  lng: number;
  title?: string;
  desc?: string;
}

const props = defineProps<{
  title?: string;
  center?: [number, number];
  zoom?: number;
  markers?: MapMarker[];
}>();

const containerRef = ref<HTMLElement>();

let _AMap: any = null;
let amap: any = null;
let mapMarkers: any[] = [];

const MAP_PLUGINS = ["AMap.MarkerClusterer"];

async function initMap() {
  if (!containerRef.value) return;

  try {
    _AMap = await AMapLoader.load({
      key: (import.meta as any).env.VITE_AMAP_KEY,
      version: "2.0",
      plugins: MAP_PLUGINS,
    });
  } catch (e) {
    console.error("[MapCard] AMap 加载失败:", e);
    return;
  }

  const center = props.center?.[0] != null
    ? [props.center[0], props.center[1]]
    : [113.29, 22.81];
  const zoom = props.zoom ?? 12;

  amap = new _AMap.Map(containerRef.value, {
    resizeEnable: true,
    center,
    zoom,
    pitch: 0,
    rotation: 0,
    mapStyle: "amap://styles/light",
  });

  renderMarkers();
}

function renderMarkers() {
  if (!_AMap || !amap || !props.markers?.length) return;

  mapMarkers.forEach((mk) => mk.setMap(null));
  mapMarkers.length = 0;

  const points: [number, number][] = [];

  props.markers.forEach((m) => {
    const lng = Number(m.lng);
    const lat = Number(m.lat);
    if (isNaN(lng) || isNaN(lat)) return;

    points.push([lng, lat]);

    const content = m.title
      ? `<div class="map-marker-wrap"><div class="map-marker-dot"></div><span class="map-marker-label">${m.title}</span></div>`
      : `<div class="map-marker-dot"></div>`;

    const marker = new _AMap.Marker({
      position: [lng, lat],
      content,
      offset: new _AMap.Pixel(-10, -10),
      title: m.title || "",
    });

    if (m.title || m.desc) {
      marker.on("click", () => {
        const info = new _AMap.InfoWindow({
          content: `<div style="padding:6px 10px;font-size:13px;"><strong>${m.title || ""}</strong>${m.desc ? `<br><span style="color:#888;font-size:12px;">${m.desc}</span>` : ""}</div>`,
          offset: new _AMap.Pixel(0, -30),
        });
        info.open(amap, [lng, lat]);
      });
    }

    mapMarkers.push(marker);
    marker.setMap(amap);
  });

  if (points.length > 0) {
    amap.setFitView(null, false, [80, 80, 80, 80]);
  }
}

function zoomIn() {
  amap?.zoomIn();
}

function zoomOut() {
  amap?.zoomOut();
}

watch(
  () => props.markers,
  () => nextTick(renderMarkers),
  { deep: true }
);

let mapInited = false;
let observer: IntersectionObserver | null = null;

onMounted(() => {
  if (!containerRef.value) return;

  const supportsIntersection = typeof IntersectionObserver !== "undefined";
  if (supportsIntersection) {
    observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting && !mapInited) {
          mapInited = true;
          nextTick(initMap);
          observer?.disconnect();
          observer = null;
        }
      },
      { rootMargin: "200px" }
    );
    observer.observe(containerRef.value);
  } else {
    mapInited = true;
    nextTick(initMap);
  }
});

onBeforeUnmount(() => {
  observer?.disconnect();
  mapMarkers.forEach((m) => m.setMap(null));
  if (amap) amap.destroy();
});
</script>

<style lang="scss" scoped>
.map-card {
  margin: 12px 0;
  border: 1px solid #eef0f4;
  border-radius: 12px;
  overflow: hidden;
  background: #fff;
}

.map-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: #f8fafc;
  border-bottom: 1px solid #f1f5f9;

  .map-title {
    font-size: 13px;
    font-weight: 600;
    color: #1a1a2e;
  }

  .map-badge {
    font-size: 11px;
    color: #64748b;
    background: #f1f5f9;
    padding: 2px 10px;
    border-radius: 10px;
  }
}

.map-body {
  width: 100%;
  height: 300px;
  max-height: 45vh;
  position: relative;
}

.map-zoom-controls {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 10;
  display: flex;
  flex-direction: column;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
}

.map-zoom-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  color: #334155;
  background: #fff;
  border: none;
  cursor: pointer;
  transition: background 0.12s;
  user-select: none;

  &:hover {
    background: #f1f5f9;
  }

  &:active {
    background: #e2e8f0;
  }
}

.map-zoom-divider {
  display: block;
  height: 1px;
  margin: 0 8px;
  background: #e2e8f0;
}
</style>

<style lang="scss">
.map-marker-wrap {
  display: flex;
  align-items: center;
  gap: 4px;
}

.map-marker-dot {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #7c3aed;
  border: 2.5px solid #fff;
  box-shadow: 0 2px 6px rgba(124, 58, 237, 0.35);
  cursor: pointer;
  transition: transform 0.15s ease;

  &:hover {
    transform: scale(1.45);
  }
}

.map-marker-label {
  font-size: 12px;
  color: #333;
  background: rgba(255, 255, 255, 0.9);
  padding: 2px 6px;
  border-radius: 4px;
  white-space: nowrap;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.amap-logo,
.amap-copyright {
  display: none !important;
}
</style>
