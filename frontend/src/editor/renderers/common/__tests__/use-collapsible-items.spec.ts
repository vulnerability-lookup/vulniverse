import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { defineComponent, nextTick, ref } from "vue";

import { useCollapsibleItems } from "../use-collapsible-items";

/** The composable inside a component, for a list of `count` cards. */
function cardsOf(count: number) {
  const length = ref(count);
  let cards!: ReturnType<typeof useCollapsibleItems>;

  mount(defineComponent({
    setup() {
      cards = useCollapsibleItems(length);
      return () => null;
    },
  }));

  const open = () => Array.from({ length: length.value }, (_, index) => cards.isExpanded(index));

  return { length, cards, open };
}

describe("useCollapsibleItems", () => {
  it("opens a single card on load, but not one of several", () => {
    expect(cardsOf(1).open()).toEqual([true]);
    expect(cardsOf(3).open()).toEqual([false, false, false]);
  });

  it("opens a card that's added", async () => {
    const { length, open } = cardsOf(2);

    length.value = 3;
    await nextTick();

    expect(open()).toEqual([false, false, true]);
  });

  it("expands and collapses all cards at once", () => {
    const { cards, open } = cardsOf(3);

    cards.toggleAll();
    expect([cards.allExpanded.value, ...open()]).toEqual([true, true, true, true]);

    cards.toggleAll();
    expect([cards.allExpanded.value, ...open()]).toEqual([false, false, false, false]);
  });
});
