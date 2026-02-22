import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { useDetectionsStore } from "./detections-store";
import type { Detection, FrequencyItem } from "@/services/types.ts";

export const useAnalyticsStore = defineStore("analytics", () => {
    const detectionsStore = useDetectionsStore();

    const totalDetections = ref(0);
    const totalConfidence = ref(0);

    const maxDetection = ref<Detection | null>(null);
    const minDetection = ref<Detection | null>(null);

    const objectCounts = ref<Record<number, number>>({});
    const anomalyCounts = ref<Record<number, number>>({});
    const classInfo = ref<Record<number, { class_name: string }>>({});
    const seenTrackingIds = ref<Set<number>>(new Set());

    function processDetections(detections: Detection[]) {
        detections.forEach((det) => {
            if (det.track_id === null) return;
            if (seenTrackingIds.value.has(det.track_id)) return;
            seenTrackingIds.value.add(det.track_id);

            totalDetections.value++;
            totalConfidence.value += det.confidence;

            if (!classInfo.value[det.class_id]) {
                classInfo.value[det.class_id] = {
                    class_name: det.class_name,
                };
            }

            if (!maxDetection.value || det.confidence > maxDetection.value.confidence) {
                maxDetection.value = det;
            }

            if (!minDetection.value || det.confidence < minDetection.value.confidence) {
                minDetection.value = det;
            }

            if (det.is_anomaly) {
                anomalyCounts.value[det.class_id] =
                    (anomalyCounts.value[det.class_id] ?? 0) + 1;
            } else {
                objectCounts.value[det.class_id] =
                    (objectCounts.value[det.class_id] ?? 0) + 1;
            }
        });
    }

    function updateDetections() {
        const currentDetections = detectionsStore.detections;
        if (currentDetections.length > 0) {
            processDetections(currentDetections);
        }
    }

    function resetAnalytics() {
        totalDetections.value = 0;
        totalConfidence.value = 0;
        maxDetection.value = null;
        minDetection.value = null;
        objectCounts.value = {};
        anomalyCounts.value = {};
        classInfo.value = {};
        seenTrackingIds.value.clear();
    }

    const averageConfidence = computed(() =>
        totalDetections.value === 0
            ? 0
            : totalConfidence.value / totalDetections.value
    );

    const totalObjects = computed(() =>
        Object.values(objectCounts.value).reduce((a, b) => a + b, 0)
    );

    const totalAnomalies = computed(() =>
        Object.values(anomalyCounts.value).reduce((a, b) => a + b, 0)
    );

    const totalObjectDistribution = computed(() =>
        totalDetections.value === 0
            ? 0
            : totalObjects.value / totalDetections.value
    );

    const totalAnomalyDistribution = computed(() =>
        totalDetections.value === 0
            ? 0
            : totalAnomalies.value / totalDetections.value
    );

    function buildFrequencyList(
        counts: Record<number, number>,
        divisor: number
    ): FrequencyItem[] {
        if (divisor === 0) return [];

        return Object.entries(counts).map(([id, count]) => ({
            class_id: Number(id),
            class_name: classInfo.value[Number(id)]?.class_name ?? "Unknown",
            count,
            frequency: count / divisor,
        }));
    }

    const objectFrequencyByObjects = computed<FrequencyItem[]>(() =>
        buildFrequencyList(objectCounts.value, totalObjects.value)
    );

    const anomalyFrequencyByAnomalies = computed<FrequencyItem[]>(() =>
        buildFrequencyList(anomalyCounts.value, totalAnomalies.value)
    );

    const objectFrequencyByDetections = computed<FrequencyItem[]>(() =>
        buildFrequencyList(objectCounts.value, totalDetections.value)
    );

    const anomalyFrequencyByDetections = computed<FrequencyItem[]>(() =>
        buildFrequencyList(anomalyCounts.value, totalDetections.value)
    );

    function getFrequencyFromList(list: FrequencyItem[], classId: number): number {
        const item = list.find(item => item.class_id === classId)
        if (!item) return 0
        return Number((item.frequency * 100).toFixed(2))
    }

    function getFrequenciesForClass(classId: number) {
        return {
            objectByObjects: getFrequencyFromList(
                objectFrequencyByObjects.value,
                classId
            ),
            objectByDetections: getFrequencyFromList(
                objectFrequencyByDetections.value,
                classId
            ),
            anomalyByAnomalies: getFrequencyFromList(
                anomalyFrequencyByAnomalies.value,
                classId
            ),
            anomalyByDetections: getFrequencyFromList(
                anomalyFrequencyByDetections.value,
                classId
            ),
        };
    }

    return {
        updateDetections,
        resetAnalytics,
        totalDetections,
        totalObjects,
        totalAnomalies,
        totalObjectDistribution,
        totalAnomalyDistribution,
        minDetection,
        maxDetection,
        averageConfidence,
        objectFrequencyByObjects,
        anomalyFrequencyByAnomalies,
        objectFrequencyByDetections,
        anomalyFrequencyByDetections,
        getFrequencyFromList,
        getFrequenciesForClass,
    };
});