import assert from "node:assert/strict";
import { describe, it } from "node:test";

// @ts-expect-error -- Node's built-in TypeScript runner requires the extension.
import { invalidateMuhurtaPlace, selectedMuhurtaPlace } from "./muhurta-place.ts";

describe("Muhurta place selection", () => {
  it("applies an Athlone result as one coherent place/coordinate/zone context", () => {
    assert.deepEqual(
      selectedMuhurtaPlace({
        label: "Athlone, County Westmeath, Ireland",
        lat: 53.4239,
        lon: -7.9407,
        timezone: "Europe/Dublin",
      }),
      {
        place: "Athlone, County Westmeath, Ireland",
        latitude: "53.4239",
        longitude: "-7.9407",
        timezone: "Europe/Dublin",
      },
    );
  });

  it("clears stale Dublin geometry when the place label is edited", () => {
    assert.deepEqual(invalidateMuhurtaPlace("Athlone"), {
      place: "Athlone",
      latitude: "",
      longitude: "",
      timezone: "",
    });
  });
});
