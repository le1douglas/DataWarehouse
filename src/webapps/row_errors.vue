<!--
the box of RowErrors: the errors of the grid cell under the pointer, one per line, next to the pointer.
it is teleported into the .ag-root-wrapper of the hovered grid, where the theme's variables are defined, so it takes
the colors of the theme's tooltip, bordered in the red of an error row. until a cell is hovered there is no box.
it is fixed at the pointer and lets the mouse through to the cell below
-->
<template>
  <Teleport v-if="wrapper" :to="wrapper">
    <div v-show="text" class="row-errors" :style="{ left: x + 12 + 'px', top: y + 12 + 'px' }">{{ text }}</div>
  </Teleport>
</template>

<script>
export default {
  data() {
    return { wrapper: null, descriptions: [], x: 0, y: 0 };
  },
  computed: {
    text() {
      return this.descriptions.join("\n");
    },
  },
  // the box follows the pointer over the whole page, so it is in place before the next cell shows it
  mounted() {
    this.follow = (event) => {
      this.x = event.clientX;
      this.y = event.clientY;
    };
    document.addEventListener("mousemove", this.follow);
  },
  unmounted() {
    document.removeEventListener("mousemove", this.follow);
  },
  methods: {
    // the errors of the hovered cell: those in the whole row, with no target_column, and those in its column
    show(params) {
      this.wrapper = params.event.target.closest(".ag-root-wrapper");
      this.descriptions = params.data.errors
        .filter((error) => !error.target_column || error.target_column === params.colDef.field)
        .map((error) => error.description);
      this.follow(params.event);
    },
    hide() {
      this.descriptions = [];
    },
  },
};
</script>

<style>
.row-errors {
  position: fixed;
  z-index: 1000;
  pointer-events: none;
  white-space: pre-line;
  padding: 4px 8px;
  background-color: var(--ag-tooltip-background-color);
  color: var(--ag-tooltip-text-color);
  border: solid 1px var(--ag-invalid-color);
  border-radius: var(--ag-border-radius);
}
</style>
