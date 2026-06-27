/** CesiumJS 3D viewer: orbits, TCA marker, timeline. */

const KM_TO_M = 1000;

let viewer = null;
let satEntity = null;
let debEntity = null;
let tcaEntity = null;

export function initViewer() {
  viewer = new Cesium.Viewer("cesiumContainer", {
    baseLayerPicker: false,
    geocoder: false,
    homeButton: true,
    sceneModePicker: false,
    navigationHelpButton: false,
    animation: true,
    timeline: true,
    fullscreenButton: false,
    terrain: Cesium.Terrain.NONE,
    shouldAnimate: true,
  });

  viewer.imageryLayers.removeAll();
  viewer.imageryLayers.addImageryProvider(
    new Cesium.TileMapServiceImageryProvider({
      url: Cesium.buildModuleUrl("Assets/Textures/NaturalEarthII"),
    })
  );

  viewer.scene.skyAtmosphere.show = true;
  viewer.clock.multiplier = 60;
  return viewer;
}

function buildSampledProperty(points) {
  const property = new Cesium.SampledPositionProperty(Cesium.ReferenceFrame.INERTIAL);
  for (const pt of points) {
    const time = Cesium.JulianDate.fromIso8601(
      pt.time.endsWith("Z") ? pt.time : `${pt.time}Z`
    );
    const pos = new Cesium.Cartesian3(
      pt.position_km.x * KM_TO_M,
      pt.position_km.y * KM_TO_M,
      pt.position_km.z * KM_TO_M
    );
    property.addSample(time, pos);
  }
  return property;
}

function buildOrbitPolyline(points, color) {
  const positions = points.map(
    (pt) =>
      new Cesium.Cartesian3(
        pt.position_km.x * KM_TO_M,
        pt.position_km.y * KM_TO_M,
        pt.position_km.z * KM_TO_M
      )
  );
  return {
    polyline: {
      positions,
      width: 2,
      material: color,
    },
    referenceFrame: Cesium.ReferenceFrame.INERTIAL,
  };
}

export function clearScene() {
  if (!viewer) return;
  viewer.entities.removeAll();
  satEntity = null;
  debEntity = null;
  tcaEntity = null;
}

export function showOrbits({ satellite, debris, tcaTime, tcaPositionKm }) {
  if (!viewer) initViewer();
  clearScene();

  const start = Cesium.JulianDate.fromIso8601(
    satellite.points[0].time.endsWith("Z")
      ? satellite.points[0].time
      : `${satellite.points[0].time}Z`
  );
  const stop = Cesium.JulianDate.fromIso8601(
    satellite.points[satellite.points.length - 1].time.endsWith("Z")
      ? satellite.points[satellite.points.length - 1].time
      : `${satellite.points[satellite.points.length - 1].time}Z`
  );

  viewer.clock.startTime = start.clone();
  viewer.clock.stopTime = stop.clone();
  viewer.clock.currentTime = start.clone();
  viewer.timeline.zoomTo(start, stop);

  viewer.entities.add({
    name: `${satellite.name} orbit`,
    ...buildOrbitPolyline(satellite.points, Cesium.Color.DODGERBLUE),
  });

  const satPos = buildSampledProperty(satellite.points);
  satEntity = viewer.entities.add({
    name: satellite.name,
    position: satPos,
    point: {
      pixelSize: 10,
      color: Cesium.Color.DODGERBLUE,
      outlineColor: Cesium.Color.WHITE,
      outlineWidth: 1,
    },
    path: {
      leadTime: 0,
      trailTime: 3600,
      width: 1,
      material: Cesium.Color.DODGERBLUE.withAlpha(0.5),
    },
  });

  if (debris) {
    viewer.entities.add({
      name: `${debris.name} orbit`,
      ...buildOrbitPolyline(debris.points, Cesium.Color.RED),
    });

    const debPos = buildSampledProperty(debris.points);
    debEntity = viewer.entities.add({
      name: debris.name,
      position: debPos,
      point: {
        pixelSize: 10,
        color: Cesium.Color.RED,
        outlineColor: Cesium.Color.WHITE,
        outlineWidth: 1,
      },
      path: {
        leadTime: 0,
        trailTime: 3600,
        width: 1,
        material: Cesium.Color.RED.withAlpha(0.5),
      },
    });
  }

  if (tcaTime && tcaPositionKm) {
    const tca = Cesium.JulianDate.fromIso8601(
      tcaTime.endsWith("Z") ? tcaTime : `${tcaTime}Z`
    );
    const tcaPos = new Cesium.Cartesian3(
      tcaPositionKm.x * KM_TO_M,
      tcaPositionKm.y * KM_TO_M,
      tcaPositionKm.z * KM_TO_M
    );
    tcaEntity = viewer.entities.add({
      name: "TCA",
      position: tcaPos,
      referenceFrame: Cesium.ReferenceFrame.INERTIAL,
      point: {
        pixelSize: 14,
        color: Cesium.Color.YELLOW,
        outlineColor: Cesium.Color.BLACK,
        outlineWidth: 2,
      },
      label: {
        text: "TCA",
        font: "14px sans-serif",
        fillColor: Cesium.Color.YELLOW,
        pixelOffset: new Cesium.Cartesian2(0, -18),
      },
    });
    viewer.clock.currentTime = tca.clone();
  }

  viewer.trackedEntity = satEntity;
}

export function getTcaPositionFromOrbits(satPoints, debPoints, tcaIso) {
  const target = tcaIso.replace("+00:00", "Z");
  let bestSat = satPoints[0];
  let bestDeb = debPoints[0];
  let bestDiff = Infinity;

  const len = Math.min(satPoints.length, debPoints.length);
  for (let i = 0; i < len; i++) {
    const t = satPoints[i].time.replace("+00:00", "Z");
    const diff = Math.abs(new Date(t) - new Date(target));
    if (diff < bestDiff) {
      bestDiff = diff;
      bestSat = satPoints[i];
      bestDeb = debPoints[i];
    }
  }

  const sx = bestSat.position_km.x;
  const sy = bestSat.position_km.y;
  const sz = bestSat.position_km.z;
  const dx = bestDeb.position_km.x;
  const dy = bestDeb.position_km.y;
  const dz = bestDeb.position_km.z;

  return {
    x: (sx + dx) / 2,
    y: (sy + dy) / 2,
    z: (sz + dz) / 2,
  };
}
