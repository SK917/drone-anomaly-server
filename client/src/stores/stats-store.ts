import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type { StatsResponse } from "@/services/types.ts";

export const useStatsStore = defineStore("stats", () => {
    const stats = ref<StatsResponse | null>(null);
    const loading = ref(false);
    const error = ref<string | null>(null);

    function applyData(payload: StatsResponse) {
        stats.value = payload;
    }

    const has_stream = computed(() => stats.value?.has_stream);
    const is_processing = computed(() => stats.value?.is_processing);
    const interference_count = computed(() => stats.value?.inference_count);
    const interference_fps = computed(() => stats.value?.inference_fps);

    return {
        stats,
        loading,
        error,
        applyData,
        has_stream,
        is_processing,
        interference_count,
        interference_fps,
    }
});