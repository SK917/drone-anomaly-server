import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { getAnomalies } from "@/services/anomalies-service";
import { useAnalyticsStore } from "./analytics-store";
import type { AnomaliesResponse, ClassItem, Detection } from "@/services/types.ts";

export const useAnomaliesStore = defineStore("anomalies", () => {
    const analyticsStore = useAnalyticsStore();
    const anomalyData = ref<AnomaliesResponse | null>(null);
    const loading = ref(false);
    const error = ref<string | null>(null);

    async function fetchAnomalies() {
        loading.value = true;
        error.value = null;

        try {
            anomalyData.value = await getAnomalies();

        } catch (err) {
            error.value = "Failed to fetch anomalies";
            console.error(err);
        } finally {
            loading.value = false;
        }
    }

    const count = computed(() => {
        return anomalyData.value?.count ?? 0;
    });

    const classes = computed(() => {
        return anomalyData.value?.classes ?? [];
    })

    const anomalies = computed(() => {
        const allAnomalies = anomalyData.value?.anomalies ?? [];
        return allAnomalies.filter(anomaly => 
            anomaly.track_id !== null && 
            analyticsStore.seenTrackingIds.has(anomaly.track_id)
        );
    });

    const rawAnomalyData = computed(() => {
        return anomalyData.value?.anomalies ?? [];
    })

    return {
        fetchAnomalies,
        count,
        classes,
        anomalies,
        rawAnomalyData
    }
});