<script setup lang="ts">
import type { FrequencyItem } from '@/services/types';
import AnalyticsCard from './AnalyticsCard.vue';

defineProps<{
    items: FrequencyItem[];
}>();
</script>

<template>
    <div class="flex flex-row gap-2 items-center bg-gray-900 min-h-32 rounded-sm overflow-x-auto detections-scroll">
        <div
            v-if="items.length > 0"
            v-for="item in items"
            :key="item.class_id"
            class="w-full"
        >
            <AnalyticsCard
                :num="item.frequency"
                :label="item.class_name"
                :otherInfo="''"
                :isPercent="true"
            />
        </div>
        <div v-else class="text-gray-400 text-md p-4 text-center">
            No items to display.
        </div>
    </div>
</template>


<style scoped>
    /* Chrome, Edge, Safari */
    .detections-scroll::-webkit-scrollbar {
    width: 8px;
    }

    .detections-scroll::-webkit-scrollbar-track {
    background: #1f2937; /* gray-800 */
    }

    .detections-scroll::-webkit-scrollbar-thumb {
    background-color: #4b5563; /* gray-600 */
    border-radius: 6px;
    }

    .detections-scroll::-webkit-scrollbar-thumb:hover {
    background-color: #6b7280; /* gray-500 */
    }

    /* Firefox */
    .detections-scroll {
    scrollbar-width: thin;
    scrollbar-color: #4b5563 #1f2937;
    }
</style>