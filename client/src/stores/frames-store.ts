import { defineStore } from "pinia";
import { ref } from "vue";
import { getAnnotatedFrameUrl } from "@/services/frames-service";

export const useFramesStore = defineStore("frames", () => {
    const frameUrl = ref<string>("");

    let intervalId: number | null = null;

    function getNewFrame() {
        frameUrl.value = getAnnotatedFrameUrl();
    }

    //async polling functions to continuously fetch from backend
    function startPolling(intervalMs = 50) {
        if (intervalId !== null) return;

        const poll = async () => {
            await getNewFrame();
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

    return {
        frameUrl,
        getNewFrame,
        startPolling,
        stopPolling,
    };
});