import { createRouter, createWebHistory } from "vue-router";
import Home from "@/views/Home.vue";

const DEFAULT_TITLE = "Drone Analytics Dashboard";

const router = createRouter({
    history: createWebHistory(),
    routes: [
        {
            path: "/",
            name: "Home",
            component: Home,
            meta: {title: "Home"}
        },
    ],
});

router.afterEach((to) => {
    const title = to.meta.title as string | undefined;
    document.title = title
        ? `${title} - ${DEFAULT_TITLE}`
        : DEFAULT_TITLE;
});

export default router;




/* 
//old stuff
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [],
})

export default router
*/
