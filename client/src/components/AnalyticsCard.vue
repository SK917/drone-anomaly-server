<script setup lang="ts">
    import { computed } from 'vue';

    interface Props {
        num: number
        label: string
        otherInfo: string
        isPercent: boolean
    }

    const props = defineProps<Props>();
    
    const numFixed = computed(() => {
        const baseValue = props.isPercent ? props.num * 100 : props.num;
        return baseValue.toFixed(2);
    }) 

    // Circle calcs for graphic
    const radius = 16; 
    const circumference = 2 * Math.PI * radius;
    
    const strokeDashoffset = computed(() => {
        const percent = Math.min(Math.max(props.num * 100, 0), 100);
        return circumference - (percent / 100) * circumference;
    });
</script>

<template>
    <div class="flex flex-col items-center justify-between p-4 w-auto min-w-40 min-h-32 border border-gray-600 rounded-sm hover:border-yellow-600">
        
        <div class="flex items-center justify-center gap-3">
            <template v-if="isPercent">
                <svg class="w-10 h-10 transform -rotate-90 shrink-0">
                    <circle
                        cx="20" cy="20" :r="radius"
                        stroke="currentColor" stroke-width="4" fill="transparent"
                        class="text-gray-700"
                    />
                    <circle
                        cx="20" cy="20" :r="radius"
                        stroke="currentColor" stroke-width="4" fill="transparent"
                        stroke-linecap="round"
                        :stroke-dasharray="circumference"
                        :style="{ strokeDashoffset: strokeDashoffset }"
                        class="text-yellow-600 transition-all duration-700 ease-in-out"
                    />
                </svg>
                
                <div class="text-3xl text-amber-200 font-tektur whitespace-nowrap">
                    {{ numFixed }}%
                </div>
            </template>

            <div v-else class="text-4xl text-amber-200 font-tektur py-2">
                {{ num }}
            </div>
        </div>

        <div class="flex flex-col items-center mt-1">
            <div v-if="otherInfo" class="text-gray-400 text-xs font-orbit text-center">
                {{ otherInfo }}
            </div>
            <div class="text-white text-sm pt-1 font-semibold font-orbit text-center">
                {{ label }}
            </div>
        </div>
    </div>
</template>