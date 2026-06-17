<template>
  <div class="route-card">
    <div class="route-header">
      <span class="route-title">🗺️ 路线规划</span>
      <span class="route-badge">{{ modeLabel }}</span>
    </div>

    <div class="route-tabs">
      <button
        v-for="m in MODES"
        :key="m.key"
        class="route-tab"
        :class="{ active: currentMode === m.key }"
        @click="switchMode(m.key)"
      >{{ m.label }}</button>
    </div>

    <div ref="containerRef" class="route-map-body">
      <div v-if="loading" class="route-loading">
        <span>路线计算中...</span>
      </div>
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

    <div v-if="currentMode === 'driving' && altRoutes.length > 1" class="route-alt-tabs">
      <button
        v-for="(r, i) in altRoutes"
        :key="i"
        class="route-alt-tab"
        :class="{ active: activeRouteIndex === i }"
        @click="selectRoute(i)"
      >
        {{ r.label }}
        <span class="route-alt-meta">{{ r.distance }} · {{ r.time }}</span>
      </button>
    </div>

    <div v-if="routeSummary" class="route-summary">
      <div class="summary-item">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#4f46e5" stroke-width="2">
          <path d="M2 12h20M12 2v20" />
        </svg>
        <span>{{ routeSummary.distance }}</span>
      </div>
      <div class="summary-item">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#4f46e5" stroke-width="2">
          <circle cx="12" cy="12" r="10" />
          <path d="M12 6v6l4 2" />
        </svg>
        <span>{{ routeSummary.time }}</span>
      </div>
    </div>

    <details v-if="steps.length > 0" class="route-steps">
      <summary class="steps-toggle">查看详细步骤 ({{ steps.length }} 步)</summary>
      <ol class="steps-list">
        <li v-for="(s, i) in steps" :key="i" class="step-item">
          <span class="step-icon">{{ stepIcon(s.instruction) }}</span>
          <span class="step-text">{{ s.instruction }}</span>
          <span class="step-dist">{{ s.distance }}</span>
        </li>
      </ol>
    </details>

    <div v-if="error" class="route-error">{{ error }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from "vue";
import AMapLoader from "@amap/amap-jsapi-loader";

interface RoutePoint {
  lng: number;
  lat: number;
  name: string;
}

type RouteMode = "driving" | "walking" | "riding" | "transit";

const props = defineProps<{
  mode?: string;
  from?: RoutePoint;
  to?: RoutePoint;
}>();

const MODES: { key: RouteMode; label: string }[] = [
  { key: "driving", label: "驾车" },
  { key: "walking", label: "步行" },
  { key: "riding", label: "骑行" },
  { key: "transit", label: "公交" },
];

const MODE_LABELS: Record<string, string> = {
  driving: "驾车", walking: "步行", riding: "骑行", transit: "公交",
};

const containerRef = ref<HTMLElement>();
const loading = ref(true);
const error = ref("");
const currentMode = ref<RouteMode>("driving");
const activeRouteIndex = ref(0);

interface AltRoute { label: string; distance: string; time: string; }
const altRoutes = ref<AltRoute[]>([]);
const routeSummary = ref<{ distance: string; time: string } | null>(null);
const steps = ref<{ instruction: string; distance: string }[]>([]);

const modeLabel = computed(() => MODE_LABELS[currentMode.value] || "驾车");

let _AMap: any = null;
let amap: any = null;
let startMarker: any = null;
let endMarker: any = null;
let routePolyline: any = null;
let drivingRoutes: any[] = [];

function haversine(a: RoutePoint, b: RoutePoint): number {
  const R = 6371;
  const dLat = ((b.lat - a.lat) * Math.PI) / 180;
  const dLng = ((b.lng - a.lng) * Math.PI) / 180;
  const lat1 = (a.lat * Math.PI) / 180;
  const lat2 = (b.lat * Math.PI) / 180;
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.asin(Math.sqrt(h));
}

function resolveInitialMode(): RouteMode {
  const m = props.mode as RouteMode;
  if (m && m !== "auto") return m;
  if (!props.from || !props.to) return "driving";
  const dist = haversine(props.from, props.to);
  if (dist < 1) return "walking";
  if (dist < 10) return "riding";
  return "driving";
}

async function initMap() {
  if (!containerRef.value) return;

  try {
    _AMap = await AMapLoader.load({
      key: (import.meta as any).env.VITE_AMAP_KEY,
      version: "2.0",
    });
  } catch (e) {
    console.error("[RouteCard] AMap 加载失败:", e);
    error.value = "地图加载失败";
    loading.value = false;
    return;
  }

  const center: [number, number] = props.from
    ? [props.from.lng, props.from.lat]
    : [113.29, 22.81];

  amap = new _AMap.Map(containerRef.value, {
    resizeEnable: true,
    center,
    zoom: 13,
    mapStyle: "amap://styles/light",
    zoomEnable: true,
    dragEnable: true,
    doubleClickZoom: true,
    scrollWheel: true,
    touchZoom: true,
  });

  currentMode.value = resolveInitialMode();
  await searchRoute();
}

function zoomIn() { amap?.zoomIn(); }
function zoomOut() { amap?.zoomOut(); }

function clearRoute() {
  if (routePolyline) { routePolyline.setMap(null); routePolyline = null; }
  if (startMarker) { startMarker.setMap(null); startMarker = null; }
  if (endMarker) { endMarker.setMap(null); endMarker = null; }
}

function renderMarkers(lng1: number, lat1: number, lng2: number, lat2: number) {
  clearRoute();
  startMarker = new _AMap.Marker({
    position: [lng1, lat1],
    content: `<div class="route-marker start"><span>起</span></div>`,
    offset: new _AMap.Pixel(-16, -40),
    zIndex: 120,
  });
  startMarker.setMap(amap);
  endMarker = new _AMap.Marker({
    position: [lng2, lat2],
    content: `<div class="route-marker end"><span>终</span></div>`,
    offset: new _AMap.Pixel(-16, -40),
    zIndex: 120,
  });
  endMarker.setMap(amap);
}

function formatDistance(meters: number): string {
  if (meters < 1000) return `${meters} 米`;
  return `${(meters / 1000).toFixed(1)} 公里`;
}

function formatTime(seconds: number): string {
  if (seconds < 60) return `${seconds} 秒`;
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h} 小时 ${m} 分钟`;
  return `${m} 分钟`;
}

async function searchRoute() {
  if (!amap || !_AMap || !props.from || !props.to) return;
  loading.value = true;
  error.value = "";
  altRoutes.value = [];
  routeSummary.value = null;
  steps.value = [];

  const mode = currentMode.value;
  const fromLL: [number, number] = [props.from.lng, props.from.lat];
  const toLL: [number, number] = [props.to.lng, props.to.lat];

  try {
    if (mode === "driving") {
      const Dr = (_AMap as any).DrivingRoute;
      if (!Dr) { error.value = "驾车路线服务加载失败"; loading.value = false; return; }
      new Dr({ map: amap, autoFitView: true }).search(fromLL, toLL, (status: string, result: any) => {
        loading.value = false;
        if (status === "complete" && result.routes?.length) {
          processDrivingRoutes(result.routes);
          renderMarkers(props.from!.lng, props.from!.lat, props.to!.lng, props.to!.lat);
        } else { error.value = "驾车路线计算失败"; }
      });
      return;
    }
    if (mode === "walking") {
      const W = (_AMap as any).WalkingRoute;
      if (!W) { error.value = "步行路线服务加载失败"; loading.value = false; return; }
      new W({ map: amap, autoFitView: true }).search(fromLL, toLL, (status: string, result: any) => {
        loading.value = false;
        if (status === "complete" && result.routes?.length) {
          processSingleRoute(result.routes[0]);
          renderMarkers(props.from!.lng, props.from!.lat, props.to!.lng, props.to!.lat);
        } else { error.value = "步行路线计算失败"; }
      });
      return;
    }
    if (mode === "riding") {
      const R = (_AMap as any).RidingRoute;
      if (!R) { error.value = "骑行路线服务加载失败"; loading.value = false; return; }
      new R({ map: amap, autoFitView: true }).search(fromLL, toLL, (status: string, result: any) => {
        loading.value = false;
        if (status === "complete" && result.routes?.length) {
          processSingleRoute(result.routes[0]);
          renderMarkers(props.from!.lng, props.from!.lat, props.to!.lng, props.to!.lat);
        } else { error.value = "骑行路线计算失败"; }
      });
      return;
    }
    if (mode === "transit") {
      const T = (_AMap as any).TransferRoute;
      if (!T) { error.value = "公交路线服务加载失败"; loading.value = false; return; }
      new T({ map: amap, city: props.from?.name || "", autoFitView: true }).search(fromLL, toLL, (status: string, result: any) => {
        loading.value = false;
        if (status === "complete" && result.routes?.length) {
          processTransitRoute(result.routes[0]);
          renderMarkers(props.from!.lng, props.from!.lat, props.to!.lng, props.to!.lat);
        } else { error.value = "公交路线计算失败"; }
      });
      return;
    }
  } catch (e: any) {
    console.error("[RouteCard] 路线计算异常:", e);
    loading.value = false;
    error.value = "路线计算异常，请重试";
  }
}

function processDrivingRoutes(routes: any[]) {
  drivingRoutes = routes;
  altRoutes.value = routes.map((r: any, i: number) => ({
    label: i === 0 ? "最快" : i === 1 ? "最短" : `方案 ${i + 1}`,
    distance: formatDistance(r.distance || 0),
    time: formatTime(r.time || 0),
  }));
  selectDrivingRoute(0);
}

function selectDrivingRoute(i: number) {
  activeRouteIndex.value = i;
  const route = drivingRoutes[i];
  if (route) {
    routeSummary.value = {
      distance: formatDistance(route.distance || 0),
      time: formatTime(route.time || 0),
    };
    steps.value = (route.steps || []).map((s: any) => ({
      instruction: s.instruction || s.road || "",
      distance: formatDistance(s.distance || 0),
    }));
  }
}

function processSingleRoute(route: any) {
  if (!route) return;
  routeSummary.value = {
    distance: formatDistance(route.distance || 0),
    time: formatTime(route.time || 0),
  };
  steps.value = (route.steps || []).map((s: any) => ({
    instruction: s.instruction || s.road || "",
    distance: formatDistance(s.distance || 0),
  }));
}

function processTransitRoute(route: any) {
  if (!route) return;
  routeSummary.value = {
    distance: route.distance ? formatDistance(route.distance) : "—",
    time: route.time ? formatTime(route.time) : "—",
  };
  const transitSteps: { instruction: string; distance: string }[] = [];
  if (route.segments) {
    route.segments.forEach((seg: any) => {
      if (seg.transit) {
        transitSteps.push({
          instruction: `🚌 ${seg.transit.lines?.[0]?.name || "公交"} — ${seg.transit.on_station?.name || ""} → ${seg.transit.off_station?.name || ""}`,
          distance: formatDistance(seg.transit.distance || 0),
        });
      }
      if (seg.walking) {
        transitSteps.push({
          instruction: `🚶 步行至 ${seg.walking.destination || "下一站"}`,
          distance: formatDistance(seg.walking.distance || 0),
        });
      }
    });
  }
  steps.value = transitSteps;
}

function selectRoute(i: number) { selectDrivingRoute(i); }

async function switchMode(mode: RouteMode) {
  if (currentMode.value === mode) return;
  currentMode.value = mode;
  activeRouteIndex.value = 0;
  amap?.clearMap();
  startMarker = null;
  endMarker = null;
  routePolyline = null;
  await searchRoute();
}

function stepIcon(instruction: string): string {
  if (instruction.includes("左转") || instruction.includes("左拐")) return "↰";
  if (instruction.includes("右转") || instruction.includes("右拐")) return "↱";
  if (instruction.includes("直行")) return "↑";
  if (instruction.includes("调头") || instruction.includes("掉头")) return "↶";
  if (instruction.includes("到达") || instruction.includes("目的")) return "🏁";
  if (instruction.includes("步行")) return "🚶";
  if (instruction.includes("公交")) return "🚌";
  if (instruction.includes("地铁")) return "🚇";
  return "•";
}

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
  if (startMarker) startMarker.setMap(null);
  if (endMarker) endMarker.setMap(null);
  if (routePolyline) routePolyline.setMap(null);
  if (amap) amap.destroy();
});
</script>

<style lang="scss" scoped>
.route-card {
  margin: 12px 0;
  border: 1px solid #eef0f4;
  border-radius: 12px;
  overflow: hidden;
  background: #fff;
}

.route-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: #f8fafc;
  border-bottom: 1px solid #f1f5f9;

  .route-title { font-size: 13px; font-weight: 600; color: #1a1a2e; }
  .route-badge { font-size: 11px; color: #64748b; background: #f1f5f9; padding: 2px 10px; border-radius: 10px; }
}

.route-tabs {
  display: flex;
  gap: 4px;
  padding: 8px 12px;
  background: #fff;
  border-bottom: 1px solid #f1f5f9;
}

.route-tab {
  flex: 1;
  padding: 6px 0;
  font-size: 12px;
  font-weight: 500;
  color: #64748b;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s;

  &:hover { background: #eef2ff; color: #4f46e5; }
  &.active { background: #4f46e5; color: #fff; border-color: #4f46e5; }
}

.route-map-body {
  width: 100%;
  height: 300px;
  max-height: 45vh;
  position: relative;
}

.route-loading {
  position: absolute;
  inset: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.85);
  font-size: 13px;
  color: #64748b;
}

.map-zoom-controls {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 20;
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
  &:hover { background: #f1f5f9; }
  &:active { background: #e2e8f0; }
}

.map-zoom-divider { display: block; height: 1px; margin: 0 8px; background: #e2e8f0; }

.route-alt-tabs {
  display: flex;
  gap: 6px;
  padding: 8px 12px;
  background: #fffbeb;
  border-bottom: 1px solid #fde68a;
}

.route-alt-tab {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 6px 4px;
  font-size: 12px;
  font-weight: 500;
  color: #92400e;
  background: #fff;
  border: 1px solid #fde68a;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s;

  &.active { background: #fef3c7; border-color: #d97706; box-shadow: 0 1px 3px rgba(217, 119, 6, 0.15); }
  .route-alt-meta { font-size: 10px; font-weight: 400; color: #a16207; margin-top: 2px; }
}

.route-summary {
  display: flex;
  gap: 20px;
  padding: 12px 16px;
  background: #f8fafc;
  border-bottom: 1px solid #f1f5f9;
}

.summary-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: #1a1a2e;
}

.route-steps {
  border-top: 1px solid #f1f5f9;

  .steps-toggle {
    padding: 10px 16px;
    font-size: 12px;
    color: #4f46e5;
    cursor: pointer;
    user-select: none;
    &:hover { background: #f8fafc; }
  }

  .steps-list {
    margin: 0;
    padding: 0 16px 12px;
    list-style: none;
    max-height: 240px;
    overflow-y: auto;
  }

  .step-item {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 6px 0;
    font-size: 12px;
    color: #334155;
    border-bottom: 1px solid #f1f5f9;
    &:last-child { border-bottom: none; }
    .step-icon { flex-shrink: 0; width: 18px; text-align: center; color: #94a3b8; }
    .step-text { flex: 1; line-height: 1.5; }
    .step-dist { flex-shrink: 0; color: #94a3b8; font-size: 11px; }
  }
}

.route-error {
  padding: 16px;
  font-size: 13px;
  color: #dc2626;
  text-align: center;
  background: #fef2f2;
}
</style>

<style lang="scss">
.route-marker {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  color: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
  border: 2px solid #fff;

  &.start { background: #22c55e; }
  &.end { background: #ef4444; }

  span { line-height: 1; }
}

.amap-logo,
.amap-copyright {
  display: none !important;
}
</style>
