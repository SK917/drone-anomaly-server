import { defineStore } from "pinia";
import { ref } from "vue";

export const useSocketStore = defineStore("socket", () => {
    const socket = ref<WebSocket | null>(null);

    function send(message: object) {
        if (socket.value && socket.value.readyState === WebSocket.OPEN) {
            socket.value.send(JSON.stringify(message));
        }
    }

    return {
        socket,
        send
    };
});