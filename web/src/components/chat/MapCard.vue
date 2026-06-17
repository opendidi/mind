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

    <!-- 详情弹窗 -->
    <a-modal
      v-model:visible="modalVisible"
      :closable="false"
      :footer="null"
      width="400px"
      centered
      destroyOnClose
      wrap-class-name="map-detail-modal"
    >
      <template v-if="selectedMarker">
        <!-- 缩略图 -->
        <div class="modal-hero">
          <template v-if="selectedMarker.thumb">
            <img
              :src="selectedMarker.thumb"
              class="modal-hero-img"
              @error="(e) => { if (e.target) (e.target as HTMLImageElement).style.display = 'none' }"
            />
          </template>
          <template v-else>
            <div class="modal-hero-placeholder">
              <svg
                viewBox="0 0 24 24"
                width="36"
                height="36"
                fill="none"
                stroke="#94a3b8"
                stroke-width="1.5"
              >
                <path d="M17.5 6.5h-11l-4 8h19l-4-8z" />
                <circle cx="12" cy="16" r="3" />
              </svg>
            </div>
          </template>
          <!-- 关闭按钮 -->
          <span class="modal-close" @click="modalVisible = false">✕</span>
        </div>
        <!-- 内容 -->
        <div class="modal-body">
          <h3 class="modal-name">{{ selectedMarker.title || "未命名场景" }}</h3>
          <template v-if="selectedMarker.pano_name || selectedMarker.desc">
            <div class="modal-meta">
              <span class="meta-tag">{{ selectedMarker.pano_name ? `📁 ${selectedMarker.pano_name}` : selectedMarker.desc }}</span>
            </div>
          </template>
          <div class="modal-coord">
            <svg
              viewBox="0 0 24 24"
              width="14"
              height="14"
              fill="none"
              stroke="#7c3aed"
              stroke-width="2"
            >
              <circle cx="12" cy="10" r="3" />
              <path
                d="M12 2a8 8 0 00-8 8c0 5.4 8 12 8 12s8-6.6 8-12a8 8 0 00-8-8z"
              />
            </svg>
            <span>{{ selectedMarker.lng }}, {{ selectedMarker.lat }}</span>
          </div>
          <template v-if="selectedMarker.pano_id">
            <a
              :href="`/preview?id=${selectedMarker.pano_id}`"
              target="_blank"
              class="modal-action"
            >
              查看全景
              <svg
                viewBox="0 0 24 24"
                width="16"
                height="16"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <path d="M7 17L17 7M7 7h10v10" />
              </svg>
            </a>
          </template>
        </div>
      </template>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import {
  ref,
  reactive,
  onMounted,
  onBeforeUnmount,
  watch,
  nextTick,
} from "vue";
import AMapLoader from "@amap/amap-jsapi-loader";

interface MapMarker {
  lat: number;
  lng: number;
  title?: string;
  desc?: string;
  pano_id?: string;
  pano_name?: string;
  thumb?: string;
}

const props = defineProps<{
  title?: string;
  center?: [number, number];
  zoom?: number;
  markers?: MapMarker[];
}>();

const containerRef = ref<HTMLElement>();
const modalVisible = ref(false);
const selectedMarker = ref<MapMarker | null>(null);

let _AMap: any = null;
let amap: any = null;
let mapMarkers: any[] = [];

const MAP_PLUGINS = ["AMap.MarkerClusterer", "AMap.MarkerCluster"];

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

  const center =
    props.center?.[0] != null
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
    zoomEnable: true,
    dragEnable: true,
    doubleClickZoom: true,
    scrollWheel: true,
    touchZoom: true,
  });

  renderMarkers();
}

function onMarkerClick(m: MapMarker) {
  selectedMarker.value = m;
  modalVisible.value = true;
}

function zoomIn() {
  amap?.zoomIn();
}

function zoomOut() {
  amap?.zoomOut();
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

    const marker = new _AMap.Marker({
      position: [lng, lat],
      content: `<div class="map-marker-dot"></div>`,
      offset: new _AMap.Pixel(-9, -9),
      title: m.title || m.pano_name || "",
    });

    marker.on("click", () => onMarkerClick(m));
    mapMarkers.push(marker);
    marker.setMap(amap);
  });

  if (points.length > 0) {
    amap.setFitView(null, false, [80, 80, 80, 80]);
  }
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

  // Lazy init: only load AMap (~200KB) when card enters viewport
  const supportsIntersection =
    typeof IntersectionObserver !== "undefined";
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
      { rootMargin: "200px" } // preload when within 200px of viewport
    );
    observer.observe(containerRef.value);
  } else {
    // Fallback for older browsers
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
  height: 360px;
  max-height: 50vh;
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

// ── Modal ──

.modal-hero {
  position: relative;
  height: 180px;
  overflow: hidden;
  background: #f1f5f9;
}

.modal-hero-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.modal-hero-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f8fafc, #e2e8f0);
}

.modal-close {
  position: absolute;
  top: 10px;
  right: 12px;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  color: #fff;
  background: rgba(0, 0, 0, 0.45);
  border-radius: 50%;
  cursor: pointer;
  transition: background 0.15s;
  line-height: 1;

  &:hover {
    background: rgba(0, 0, 0, 0.65);
  }
}

.modal-body {
  padding: 20px;
}

.modal-name {
  margin: 0 0 12px;
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
  line-height: 1.3;
}

.modal-meta {
  margin-bottom: 10px;
}

.meta-tag {
  display: inline-block;
  padding: 3px 12px;
  font-size: 12px;
  color: #475569;
  background: #f1f5f9;
  border-radius: 6px;
}

.modal-coord {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 16px;
  font-size: 12px;
  color: #94a3b8;
  font-family: "SF Mono", "Consolas", monospace;
}

.modal-action {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  padding: 11px 0;
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  background: linear-gradient(135deg, #4f46e5, #7c3aed);
  border-radius: 8px;
  text-decoration: none;
  transition: box-shadow 0.15s, transform 0.1s;

  &:hover {
    box-shadow: 0 4px 14px rgba(124, 58, 237, 0.35);
    transform: translateY(-1px);
  }

  &:active {
    transform: translateY(0);
  }
}
</style>

<style lang="scss">
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

// Hide AMap logo & copyright
.amap-logo,
.amap-copyright {
  display: none !important;
}

.map-detail-modal {
  .ant-modal-body {
    padding: 0;
  }

  .ant-modal-content {
    border-radius: 12px;
    overflow: hidden;
  }
}
</style>