import api from "./api";

export function getAnnotatedFrameUrl(): string {
    return `${api.defaults.baseURL}/annotated-frame.jpg?t=${Date.now()}`;
}