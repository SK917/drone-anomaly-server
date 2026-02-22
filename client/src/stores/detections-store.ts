import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { getDetections } from "@/services/detections-service";
import type { Detection, DetectionsResponse } from "@/services/types.ts";

export const useDetectionsStore = defineStore("detections", () => {
    const data = ref<DetectionsResponse | null>(null);
    const loading = ref(false);
    const error = ref<string | null>(null);

    const detectionCounts = ref<
        Record<number, { detection: Detection; numDetects: number }>
    >({});

    const seenTrackingIds = ref<Set<number>>(new Set());

    let intervalId: number | null = null;

    async function fetchDetections() {
        loading.value = true;
        error.value = null;

        try {
            data.value = await getDetections();
            const detectionsArray = data.value?.detections ?? [];

            detectionsArray.forEach((det) => {
                if (det.track_id === null) return;
                if (seenTrackingIds.value.has(det.track_id)) return;

                seenTrackingIds.value.add(det.track_id);

                const id = det.class_id;
                const existing = detectionCounts.value[id];

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
            });

        } catch (err) {
            error.value = "Failed to fetch detections";
            console.error(err);
        } finally {
            loading.value = false;
        }
    }

    function resetCounts() {
        detectionCounts.value = {};
        seenTrackingIds.value.clear();
    }

    function startPolling(intervalMs = 100) {
        if (intervalId !== null) return;

        const poll = async () => {
            await fetchDetections();
            intervalId = window.setTimeout(poll, intervalMs);
        };

        poll();
    }

    function stopPolling() {
        if (intervalId !== null) {
            clearTimeout(intervalId);
            intervalId = null;
        }
    }

    const groupedDetections = computed(() =>
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
        fetchDetections,
        startPolling,
        stopPolling,
        resetCounts,
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