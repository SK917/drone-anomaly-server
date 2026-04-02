import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { getAnomalies } from "@/services/anomalies-service";
import { useDetectionsStore } from "./detections-store";
import type { Anomaly, ClassItem, SelectionClassItem } from "@/services/types.ts";

export const useAnomaliesStore = defineStore("anomalies", () => {
    const detectionsStore = useDetectionsStore();
    const anomalyList = ref<Anomaly[]>([]);
    const loading = ref(false);
    const error = ref<string | null>(null);
    const selectedClasses = ref<SelectionClassItem[]>([]);

    // Initial load on connect
    async function fetchAnomalies() {
        initClassConfig();
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

    function updateClassSelectStatus(id: number) {
        const item = selectedClasses.value.find(s => s.class_id === id);
        if (item) {
            item.selected = !item.selected;
        }
    }

    function initClassConfig() {
        selectedClasses.value = [
            {
                class_id: 0,
                class_name: "car",
                suggested_as_anomaly: false,
                selected: false
            },
            {
                class_id: 1,
                class_name: "cone",
                suggested_as_anomaly: false,
                selected: false
            },
            {
                class_id: 2,
                class_name: "deer",
                suggested_as_anomaly: true,
                selected: true
            },
            {
                class_id: 3,
                class_name: "fire",
                suggested_as_anomaly: true,
                selected: true
            },
            {
                class_id: 4,
                class_name: "person",
                suggested_as_anomaly: false,
                selected: false
            },
            {
                class_id: 5,
                class_name: "pig",
                suggested_as_anomaly: true,
                selected: true
            },
            {
                class_id: 6,
                class_name: "police_car",
                suggested_as_anomaly: false,
                selected: false
            },
            {
                class_id: 7,
                class_name: "wolf",
                suggested_as_anomaly: true,
                selected: true
            },
            {
                class_id: 101,
                class_name: "Crowding",
                suggested_as_anomaly: true,
                selected: true
            },
            {
                class_id: 102,
                class_name: "Traffic Jam",
                suggested_as_anomaly: true,
                selected: true
            },
            {
                class_id: 103,
                class_name: "Crash",
                suggested_as_anomaly: true,
                selected: true
            },
            {
                class_id: 104,
                class_name: "trespassing",
                suggested_as_anomaly: true,
                selected: true
            }
        ]
    }

    return {
        fetchAnomalies,
        applyDelta,
        resetAnomalies,
        updateClassSelectStatus,
        selectedClasses,
        count,
        classes,
        anomalies,
        rawAnomalyData
    }
});