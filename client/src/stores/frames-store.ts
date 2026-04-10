import { defineStore } from "pinia";
import { ref } from "vue";
import { getAnnotatedFrameUrl } from "@/services/frames-service";

export const useFramesStore = defineStore("frames", () => {
    const frameUrl = ref<string>("");

    function getNewFrame() {
        frameUrl.value = `${getAnnotatedFrameUrl()}?t=${Date.now()}`;
    }

    return {
        frameUrl,
        getNewFrame,
    };
});