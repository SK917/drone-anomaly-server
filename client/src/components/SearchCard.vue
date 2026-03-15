<script setup lang="ts">
    import type { Detection } from '@/services/types';
    import { computed } from 'vue';

    interface Props {
        anomaly: Detection
    }
    const props = defineProps<Props>();
    const confidence = computed(() =>
        Number((props.anomaly.confidence * 100).toFixed(2))
    );

</script>

<template>
    <div class="flex flex-col items-center justify-between p-2 m-2 w-auto h-auto border border-gray-600 rounded-sm hover:border-rose-800">
        <div class="flex flex-row gap-2 items-center">
            <!-- <div class="text-sm text-gray-400 font-orbit">
                Tracking ID:
            </div> -->
            <div class="text-3xl text-red-500 font-semibold font-tektur">
                {{ anomaly.track_id }}
            </div>
        </div>
        <div class="w-full h-0.5 bg-rose-800 mt-2"></div>
        <div class="p-2 flex flex-col rounded-b-sm gap-2">
            <div class="text-gray-400 text-sm font-orbit">
                Class: 
                <span class="text-red-400 font-tektur text-sm">
                    {{ anomaly.class_name }}
                </span>
            </div>
            <div class="text-gray-400 text-sm font-orbit">
                Confidence: 
                <span class="text-red-500 font-tektur font-semibold text-sm">
                    {{ confidence }}%
                </span>
            </div>
        </div>
    </div>
</template>