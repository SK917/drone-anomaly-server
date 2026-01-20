<script setup lang="ts">
    import { computed } from 'vue';
    import type { Detection } from '@/services/types';
    import { Crosshair, TriangleAlert } from 'lucide-vue-next';

    interface Props {
        detect: Detection
        numDetects: number
    }

    const props = defineProps<Props>();
    const confidence = computed(() => props.detect.confidence * 100);

</script>

<template>
    <div v-if="detect.is_anomaly" class="m-4 h-25 bg-gray-900 rounded-t-sm flex flex-col justify-between">
        <div class="p-2 pt-3 flex flex-row items-center justify-between gap-2">
            <div class="flex flex-row items-center gap-2">
                <TriangleAlert :size="35" class="pr-1 text-red-500" />
                <div class="text-3xl text-red-300">
                    {{ detect.class_name }}
                </div>
            </div>
            <div class="bg-red-700 text-red-200 rounded-3xl p-1 pl-3 pr-3">
                {{ numDetects }}
            </div>
        </div>
        <div class="p-2 w-full bg-rose-800 flex flex-row justify-between items-center rounded-b-sm gap-2">
            <div class="text-red-200 text-md">
                Confidence: 
                <span class="font-bold">
                    {{ confidence }}%
                </span>
            </div>
            <div class="text-red-200 text-md">
                Warning: Anomaly detected.
            </div>
        </div>
    </div>
    <div v-else class="m-4 h-25 bg-gray-900 rounded-t-sm flex flex-col justify-between">
        <div class="p-2 pt-3 flex flex-row items-center justify-between gap-2">
            <div class="flex flex-row items-center gap-2">
                <Crosshair :size="35" class="pr-1 text-lime-500" />
                <div class="text-3xl text-lime-300">
                    {{ detect.class_name }}
                </div>
            </div>
            <div class="bg-lime-700 text-lime-200 rounded-3xl p-1 pl-3 pr-3">
                {{ numDetects }}
            </div>
        </div>
        <div class="p-2 w-full bg-emerald-700 flex flex-row justify-between items-center rounded-b-sm gap-2">
            <div class="text-lime-200 text-md">
                Confidence: 
                <span class="font-bold">
                    {{ confidence }}%
                </span>
            </div>
            <div class="text-lime-200 text-md">
                Object detected.
            </div>
        </div>
    </div>
</template>