import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type { Detection, DetectionsResponse } from "@/services/types.ts";

export const useDetectionsStore = defineStore("detections", () => {
    const data = ref<DetectionsResponse | null>(null);
    const loading = ref(false);
    const error = ref<string | null>(null);

    const detectionCounts = ref<Record<number, { detection: Detection; numDetects: number }>>({});

    const seenTrackingIds = ref<Set<number>>(new Set());

    function applyData(payload: DetectionsResponse) {
        data.value = payload;
        const detectionsArray = payload.detections ?? [];

        detectionsArray.forEach((det) => {
            if (det.track_id === null) return;

            const id = det.class_id;
            const existing = detectionCounts.value[id];

            if (!seenTrackingIds.value.has(det.track_id)) {
                const nextSet = new Set(seenTrackingIds.value);
                nextSet.add(det.track_id);
                seenTrackingIds.value = nextSet;

                if (!existing) {
                    detectionCounts.value[id] = {
                        detection: det,
                        numDetects: 1,
                    };
                } else {
                    existing.numDetects++;
                    if (det.confidence > existing.detection.confidence) {
                        existing.detection = det;
                    }
                }
            } else {
                if (existing &&
                    existing.detection.track_id === det.track_id &&
                    det.confidence > existing.detection.confidence) {
                    existing.detection = { ...existing.detection, confidence: det.confidence };
                }
            }
        });
    }

    function resetCounts() {
        detectionCounts.value = {};
        seenTrackingIds.value = new Set();
    }

    const groupedDetections = computed<{ detection: Detection; numDetects: number }[]>(() =>
        Object.values(detectionCounts.value)
    );

    const groupedDetectionsSorted = computed(() =>
        [...groupedDetections.value].sort((a, b) =>
            Number(b.detection.is_anomaly) -
            Number(a.detection.is_anomaly)
        )
    );

    const groupedAnomalies = computed(() =>
        groupedDetections.value.filter(
            entry => entry.detection.is_anomaly
        )
    );

    const detections = computed<Detection[]>(() =>
        data.value?.detections ?? []
    );

    const anomalies = computed(() =>
        detections.value.filter(d => d.is_anomaly)
    );

    const num_detections = computed<number>(() => {
        return data.value?.num_detections ?? 0
    });

    const anomaly_count = computed<number>(() => {
        return data.value?.anomaly_count ?? 0
    });

    const has_anomaly = computed(() =>
        groupedAnomalies.value.length > 0
    );

    const timestamp = computed<number>(() =>
        data.value?.timestamp ?? 0
    );

    const inference_count = computed<number>(() =>
        data.value?.inference_count ?? 0
    );

    const inference_fps = computed<number>(() =>
        data.value?.inference_fps ?? 0
    );

    return {
        data,
        loading,
        error,
        applyData,
        resetCounts,
        seenTrackingIds,
        detectionCounts,
        groupedDetections,
        groupedDetectionsSorted,
        groupedAnomalies,
        detections,
        anomalies,
        num_detections,
        anomaly_count,
        has_anomaly,
        timestamp,
        inference_count,
        inference_fps,
    };
});