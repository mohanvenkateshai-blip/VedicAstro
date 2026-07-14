export interface MuhurtaPlaceResult {
  label: string;
  lat: number;
  lon: number;
  timezone: string;
}

export interface MuhurtaPlaceFields {
  place: string;
  latitude: string;
  longitude: string;
  timezone: string;
}

/** A selected result is one atomic context; typed edits invalidate all geometry. */
export function selectedMuhurtaPlace(result: MuhurtaPlaceResult): MuhurtaPlaceFields {
  return {
    place: result.label,
    latitude: String(result.lat),
    longitude: String(result.lon),
    timezone: result.timezone,
  };
}

export function invalidateMuhurtaPlace(typedPlace: string): MuhurtaPlaceFields {
  return { place: typedPlace, latitude: "", longitude: "", timezone: "" };
}
