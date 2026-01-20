import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { getStats } from "@/services/stats-service";
import type { StatsResponse } from "@/services/types.ts";

export const useStatsStore = defineStore("stats", () => {
    const stats = ref<StatsResponse | null>(null);
    const loading = ref(false);
    const error = ref<string | null>(null);

    let intervalId: number | null = null;

    async function fetchStats() {
        loading.value = true;
        error.value = null;

        try {
            stats.value = await getStats();
        } catch (err) {
            error.value = "Failed to fetch stats";
            console.error(err);
        } finally {
            loading.value = false;
        }
    }

    //async polling functions to continuously fetch from backend
    function startPolling(intervalMs = 100) {
        if (intervalId !== null) return;

        const poll = async () => {
            await fetchStats();
            intervalId = window.setTimeout(poll, intervalMs);
        };

        poll();
    }

    function stopPolling() {
        if (intervalId !== null) {
            clearInterval(intervalId);
            intervalId = null;
        }
    }

    //Compute values here for easy imports - can remove later if unneeded.
    const has_stream = computed(() => stats.value?.has_stream);
    const is_processing = computed(() => stats.value?.is_processing);
    const interference_count = computed(() => stats.value?.interference_count);
    const interference_fps = computed(() => stats.value?.interference_fps);

    return {
        stats,
        loading,
        error,
        fetchStats,
        startPolling,
        stopPolling,
        has_stream,
        is_processing,
        interference_count,
        interference_fps,
    }
});