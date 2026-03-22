import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { getAnomalies } from "@/services/anomalies-service";
import { useDetectionsStore } from "./detections-store";
import type { Anomaly, ClassItem } from "@/services/types.ts";

export const useAnomaliesStore = defineStore("anomalies", () => {
    const detectionsStore = useDetectionsStore();
    const anomalyList = ref<Anomaly[]>([]);
    const loading = ref(false);
    const error = ref<string | null>(null);

    // Initial load on connect
    async function fetchAnomalies() {
        loading.value = true;
        error.value = null;
        try {
            const data = await getAnomalies();
            anomalyList.value = data.anomalies ?? [];
        } catch (err) {
            error.value = "Failed to fetch anomalies";
            console.error(err);
        } finally {
            loading.value = false;
        }
    }

    // Apply incremental changes (delta) from socket updates
    function applyDelta(delta: { added: Anomaly[], updated: { track_id: number, confidence: number, bbox: number[] }[] }) {
        for (const entry of delta.added) {
            anomalyList.value.push(entry);
        }
        for (const update of delta.updated) {
            const existing = anomalyList.value.find(a => a.track_id === update.track_id);
            if (existing) {
                existing.confidence = update.confidence;
                existing.bbox = update.bbox as [number, number, number, number];
            }
        }
        // Trigger reactivity
        anomalyList.value = [...anomalyList.value];
    }

    function resetAnomalies() {
        anomalyList.value = [];
    }

    const anomalies = computed(() => {
        return anomalyList.value.filter(anomaly =>
            anomaly.track_id !== null &&
            detectionsStore.seenTrackingIds.has(anomaly.track_id)
        );
    });

    const rawAnomalyData = computed(() => anomalyList.value);

    const count = computed(() => anomalyList.value.length);

    const classes = computed(() => {
        const classMap: Record<number, ClassItem> = {};
        for (const a of anomalyList.value) {
            if (!classMap[a.class_id]) {
                classMap[a.class_id] = { class_id: a.class_id, class_name: a.class_name };
            }
        }
        return Object.values(classMap);
    });

    return {
        fetchAnomalies,
        applyDelta,
        resetAnomalies,
        count,
        classes,
        anomalies,
        rawAnomalyData
    }
});