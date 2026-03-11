import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Stage, Layer, Line, Circle } from 'react-konva';
import { DndContext, DragOverlay, useSensor, useSensors, PointerSensor } from '@dnd-kit/core';
import { ensureIds, generateId, computeCentroid } from '../../lib/floorPlanHelpers.js';
import { snapToGrid, snapToEndpoint, updateRoomsAfterWallEdit, distanceBetweenPoints, generateRoomAndWalls, mergeOverlappingWalls, SNAP_GRID } from '../../lib/wallGeometry.js';
import WallLayer from './layers/WallLayer.jsx';
import RoomLayer from './layers/RoomLayer.jsx';
import OpeningLayer from './layers/OpeningLayer.jsx';
import DimensionLayer from './layers/DimensionLayer.jsx';
import ComplianceBadgeLayer from './layers/ComplianceBadgeLayer.jsx';
import CompliancePanel from './panels/CompliancePanel.jsx';
import EditorToolbar from './panels/EditorToolbar.jsx';
import ScaleCalibration from './panels/ScaleCalibration.jsx';
import RoomTypeSelector from './panels/RoomTypeSelector.jsx';
import WallProperties from './panels/WallProperties.jsx';
import DragDropCatalog from './panels/DragDropCatalog.jsx';
import './FloorPlanEditor.css';

const MAX_HISTORY = 50;

export default function FloorPlanEditor({
  floorPlans,
  activeFloor,
  onFloorPlansChange,
  parcelId,
}) {
  const stageRef = useRef(null);
  const containerRef = useRef(null);

  // Stage viewport
  const [stageSize, setStageSize] = useState({ width: 800, height: 600 });
  const [stageScale, setStageScale] = useState(1);
  const [stagePosition, setStagePosition] = useState({ x: 0, y: 0 });

  // Editor state
  const [selectedElementId, setSelectedElementId] = useState(null);
  const [selectedElementType, setSelectedElementType] = useState(null); // 'room' | 'wall' | 'opening' | null
  const [activeTool, setActiveTool] = useState('select');
  const [scaleCalibrated, setScaleCalibrated] = useState(true);
  const [showDimensions, setShowDimensions] = useState(true);

  // Room type popover
  const [roomTypePopover, setRoomTypePopover] = useState(null);

  // Wall drawing state
  const [wallDrawStart, setWallDrawStart] = useState(null);
  const [wallDrawPreview, setWallDrawPreview] = useState(null);

  // Wall drag state (for moving entire walls)
  const [wallDragId, setWallDragId] = useState(null);
  const [wallDragOffset, setWallDragOffset] = useState(null);

  // Compliance
  const [complianceResult, setComplianceResult] = useState(null);
  const [complianceLoading, setComplianceLoading] = useState(false);
  const [showCompliance, setShowCompliance] = useState(true);
  const complianceTimerRef = useRef(null);
  const originalFloorPlanRef = useRef(null);

  // Drag and Drop state
  const [activeDragItem, setActiveDragItem] = useState(null);

  // Undo/redo
  const [editHistory, setEditHistory] = useState([]);
  const [historyIndex, setHistoryIndex] = useState(-1);

  // Configure Dnd sensors (require small distance to start drag so clicks still work)
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 5,
      },
    })
  );

  // Ensure IDs on mount / when floorPlans change
  const normalizedPlans = useMemo(() => ensureIds(floorPlans), [floorPlans]);

  const currentFloor = useMemo(() => {
    if (!normalizedPlans?.floor_plans) return null;
    if (activeFloor != null) {
      return normalizedPlans.floor_plans.find((f) => f.floor_number === activeFloor) || null;
    }
    return normalizedPlans.floor_plans[0] || null;
  }, [normalizedPlans, activeFloor]);

  const currentFloorIndex = useMemo(() => {
    if (!normalizedPlans?.floor_plans || !currentFloor) return 0;
    const idx = normalizedPlans.floor_plans.findIndex(
      (f) => f.floor_number === currentFloor.floor_number
    );
    return idx >= 0 ? idx : 0;
  }, [normalizedPlans, currentFloor]);

  // Derive selected wall object for WallProperties panel
  const selectedWall = useMemo(() => {
    if (selectedElementType !== 'wall' || !selectedElementId || !currentFloor?.walls) return null;
    return currentFloor.walls.find((w) => w.id === selectedElementId) || null;
  }, [selectedElementId, selectedElementType, currentFloor]);

  // Resize observer for container
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setStageSize({
          width: entry.contentRect.width,
          height: entry.contentRect.height,
        });
      }
    });

    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  // Fit-to-view on mount
  useEffect(() => {
    if (!currentFloor) return;

    const points = [];
    currentFloor.walls?.forEach((w) => {
      points.push(w.start, w.end);
    });
    currentFloor.rooms?.forEach((r) => {
      r.polygon?.forEach((p) => points.push(p));
    });

    if (points.length === 0) return;

    let minX = Infinity, maxX = -Infinity;
    let minY = Infinity, maxY = -Infinity;
    for (const [x, y] of points) {
      if (x < minX) minX = x;
      if (x > maxX) maxX = x;
      if (y < minY) minY = y;
      if (y > maxY) maxY = y;
    }

    const dataW = maxX - minX || 1;
    const dataH = maxY - minY || 1;
    const padding = 60;
    const scaleX = (stageSize.width - padding * 2) / dataW;
    const scaleY = (stageSize.height - padding * 2) / dataH;
    const fitScale = Math.min(scaleX, scaleY, 100);

    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;

    setStageScale(fitScale);
    setStagePosition({
      x: stageSize.width / 2 - centerX * fitScale,
      y: stageSize.height / 2 - centerY * fitScale,
    });
  }, [currentFloor, stageSize]);

  // Initialize undo history and capture original floor plan for wall-removal detection
  useEffect(() => {
    if (normalizedPlans && editHistory.length === 0) {
      setEditHistory([JSON.parse(JSON.stringify(normalizedPlans))]);
      setHistoryIndex(0);
      if (!originalFloorPlanRef.current) {
        originalFloorPlanRef.current = JSON.parse(JSON.stringify(normalizedPlans.floor_plans?.[0] || null));
      }
    }
  }, [normalizedPlans]);

  // Debounced compliance check
  const runComplianceCheck = useCallback(
    (plans) => {
      if (complianceTimerRef.current) clearTimeout(complianceTimerRef.current);

      complianceTimerRef.current = setTimeout(async () => {
        setComplianceLoading(true);
        try {
          const floorPlanData = plans?.floor_plans?.[0] || currentFloor;
          if (!floorPlanData) return;

          // Map frontend field names to backend compliance engine expectations
          const mappedRooms = (floorPlanData.rooms || []).map((r) => ({
            ...r,
            type: r.type || r.room_type || 'other',
            area_m2: r.area_m2 ?? r.area_sqm ?? null,
            name: r.name || r.id || r.room_type || 'unknown',
            center: r.center || (r.polygon ? computeCentroid(r.polygon) : null),
          }));

          const mappedOpenings = (floorPlanData.openings || []).map((o) => ({
            ...o,
            room_id: o.room_id || null,
          }));

          const mappedFloorPlan = {
            ...floorPlanData,
            rooms: mappedRooms,
            openings: mappedOpenings,
          };

          const res = await fetch('/api/v1/compliance/interior', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              floor_plan: mappedFloorPlan,
              ceiling_height_m: 2.7,
              original_floor_plan: originalFloorPlanRef.current || null,
            }),
          });
          if (res.ok) {
            setComplianceResult(await res.json());
          }
        } catch {
          // silent fail for compliance
        } finally {
          setComplianceLoading(false);
        }
      }, 300);
    },
    [parcelId, currentFloor]
  );

  // Run compliance on initial load
  useEffect(() => {
    if (normalizedPlans?.floor_plans?.length) {
      runComplianceCheck(normalizedPlans);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Deep-clone helper
  const clonePlans = useCallback(() => {
    return JSON.parse(JSON.stringify(normalizedPlans));
  }, [normalizedPlans]);

  // Push change: update parent, record undo snapshot, trigger compliance
  const pushChange = useCallback(
    (newPlans) => {
      onFloorPlansChange?.(newPlans);

      setEditHistory((prev) => {
        const trimmed = prev.slice(0, historyIndex + 1);
        const next = [...trimmed, JSON.parse(JSON.stringify(newPlans))];
        if (next.length > MAX_HISTORY) {
          return next.slice(next.length - MAX_HISTORY);
        }
        return next;
      });
      setHistoryIndex((prev) => Math.min(prev + 1, MAX_HISTORY - 1));

      runComplianceCheck(newPlans);
    },
    [onFloorPlansChange, historyIndex, runComplianceCheck]
  );

  // Undo / Redo
  const undo = useCallback(() => {
    if (historyIndex <= 0) return;
    const newIdx = historyIndex - 1;
    setHistoryIndex(newIdx);
    const snapshot = editHistory[newIdx];
    onFloorPlansChange?.(JSON.parse(JSON.stringify(snapshot)));
    runComplianceCheck(snapshot);
  }, [historyIndex, editHistory, onFloorPlansChange, runComplianceCheck]);

  const redo = useCallback(() => {
    if (historyIndex >= editHistory.length - 1) return;
    const newIdx = historyIndex + 1;
    setHistoryIndex(newIdx);
    const snapshot = editHistory[newIdx];
    onFloorPlansChange?.(JSON.parse(JSON.stringify(snapshot)));
    runComplianceCheck(snapshot);
  }, [historyIndex, editHistory, onFloorPlansChange, runComplianceCheck]);

  // ---------- Selection handlers ----------
  const handleDeselect = useCallback(() => {
    setSelectedElementId(null);
    setSelectedElementType(null);
    setRoomTypePopover(null);
  }, []);

  const handleSelectRoom = useCallback((roomId, evt) => {
    setSelectedElementId(roomId);
    setSelectedElementType('room');
    setRoomTypePopover(null);

    // If room type tool is active, show the popover
    if (activeTool === 'room') {
      const room = currentFloor?.rooms?.find((r) => r.id === roomId);
      if (room) {
        const stage = stageRef.current;
        const pointerPos = stage?.getPointerPosition();
        setRoomTypePopover({
          roomId,
          currentType: room.room_type || 'other',
          position: {
            x: pointerPos?.x ?? 200,
            y: pointerPos?.y ?? 200,
          },
        });
      }
    }
  }, [activeTool, currentFloor]);

  const handleSelectOpening = useCallback((openingId) => {
    setSelectedElementId(openingId);
    setSelectedElementType('opening');
    setRoomTypePopover(null);
  }, []);

  // ---------- Room type editing ----------
  const handleRoomTypeChange = useCallback((newType) => {
    if (!roomTypePopover) return;
    const plans = clonePlans();
    const floor = plans.floor_plans[currentFloorIndex];
    const room = floor.rooms?.find((r) => r.id === roomTypePopover.roomId);
    if (room) {
      room.room_type = newType;
      pushChange(plans);
    }
    setRoomTypePopover(null);
  }, [roomTypePopover, clonePlans, currentFloorIndex, pushChange]);

  // ---------- Wall property editing ----------
  const handleWallUpdate = useCallback((updatedWall) => {
    const plans = clonePlans();
    const floor = plans.floor_plans[currentFloorIndex];
    const idx = floor.walls?.findIndex((w) => w.id === updatedWall.id);
    if (idx >= 0) {
      floor.walls[idx] = { ...floor.walls[idx], ...updatedWall };
      pushChange(plans);
    }
  }, [clonePlans, currentFloorIndex, pushChange]);

  // ---------- Wall deletion ----------
  const handleWallDelete = useCallback((wallId) => {
    const plans = clonePlans();
    const floor = plans.floor_plans[currentFloorIndex];
    floor.walls = floor.walls?.filter((w) => w.id !== wallId) || [];
    floor.openings = floor.openings?.filter((o) => o.wall_id !== wallId) || [];
    pushChange(plans);
    handleDeselect();
  }, [clonePlans, currentFloorIndex, pushChange, handleDeselect]);

  // ---------- Wall endpoint dragging ----------
  const handleWallEndpointDrag = useCallback((wallId, endpoint, newPos) => {
    const plans = clonePlans();
    const floor = plans.floor_plans[currentFloorIndex];
    const wall = floor.walls?.find((w) => w.id === wallId);
    if (!wall) return;

    const snapped = snapToEndpoint(newPos, floor.walls || []);
    const oldPoint = endpoint === 'start' ? [...wall.start] : [...wall.end];

    if (endpoint === 'start') {
      wall.start = snapped;
    } else {
      wall.end = snapped;
    }

    floor.rooms = updateRoomsAfterWallEdit(floor.rooms, oldPoint, snapped);
    pushChange(plans);
  }, [clonePlans, currentFloorIndex, pushChange]);

  // ---------- Wall center (whole wall) dragging ----------
  const handleWallCenterDragStart = useCallback((wallId, centerPos) => {
    setWallDragId(wallId);
    setWallDragOffset(centerPos);
  }, []);

  const handleWallCenterDrag = useCallback((wallId, newCenterPos) => {
    if (!wallDragOffset) return;
    const plans = clonePlans();
    const floor = plans.floor_plans[currentFloorIndex];
    const wall = floor.walls?.find((w) => w.id === wallId);
    if (!wall) return;

    // Calculate delta from offset
    const dx = newCenterPos[0] - wallDragOffset[0];
    const dy = newCenterPos[1] - wallDragOffset[1];

    // Move both endpoints
    const newStart = [wall.start[0] + dx, wall.start[1] + dy];
    const newEnd = [wall.end[0] + dx, wall.end[1] + dy];

    wall.start = newStart;
    wall.end = newEnd;

    pushChange(plans);
    setWallDragOffset(newCenterPos);
  }, [wallDragOffset, clonePlans, currentFloorIndex, pushChange]);

  const handleWallCenterDragEnd = useCallback(() => {
    setWallDragId(null);
    setWallDragOffset(null);
  }, []);

  // ---------- Door/Window placement on wall click ----------
  const handleWallClickForOpening = useCallback((wallId) => {
    const stage = stageRef.current;
    if (!stage) return;
    const pointer = stage.getPointerPosition();
    const worldX = (pointer.x - stagePosition.x) / stageScale;
    const worldY = (pointer.y - stagePosition.y) / stageScale;

    const plans = clonePlans();
    const floor = plans.floor_plans[currentFloorIndex];
    const wall = floor.walls?.find((w) => w.id === wallId);
    if (!wall) return;

    const dx = wall.end[0] - wall.start[0];
    const dy = wall.end[1] - wall.start[1];
    const len = Math.sqrt(dx * dx + dy * dy);
    if (len === 0) return;

    const t = ((worldX - wall.start[0]) * dx + (worldY - wall.start[1]) * dy) / (len * len);
    const clampedT = Math.max(0.05, Math.min(0.95, t));
    const offset = clampedT * len;

    const openingType = activeTool === 'door' ? 'door' : 'window';
    const defaultWidth = openingType === 'door' ? 0.9 : 1.0;

    if (!floor.openings) floor.openings = [];
    const newOpening = {
      id: generateId('o'),
      type: openingType,
      wall_id: wallId,
      offset_along_wall: offset,
      width_m: defaultWidth,
    };
    if (openingType === 'door') {
      newOpening.swing_direction = 'inward';
    }
    floor.openings.push(newOpening);
    pushChange(plans);
    setSelectedElementId(newOpening.id);
    setSelectedElementType('opening');
  }, [activeTool, stagePosition, stageScale, clonePlans, currentFloorIndex, pushChange]);

  // ---------- Wall select (must be after handleWallClickForOpening) ----------
  const handleSelectWall = useCallback((wallId, action) => {
    if (activeTool === 'delete' && action === 'delete') {
      handleWallDelete(wallId);
      return;
    }
    if (activeTool === 'door' || activeTool === 'window') {
      handleWallClickForOpening(wallId);
      return;
    }
    setSelectedElementId(wallId);
    setSelectedElementType('wall');
    setRoomTypePopover(null);
  }, [activeTool, handleWallClickForOpening, handleWallDelete]);

  // ---------- Opening dragging ----------
  const handleOpeningDrag = useCallback((openingId, newOffset) => {
    const plans = clonePlans();
    const floor = plans.floor_plans[currentFloorIndex];
    const opening = floor.openings?.find((o) => o.id === openingId);
    if (opening) {
      opening.offset_along_wall = newOffset;
      pushChange(plans);
    }
  }, [clonePlans, currentFloorIndex, pushChange]);

  // ---------- Stage click for wall drawing / deselect ----------
  const handleStageClick = useCallback((e) => {
    if (e.target !== e.target.getStage()) return;

    const stage = stageRef.current;
    if (!stage) return;
    const pointer = stage.getPointerPosition();
    const worldX = (pointer.x - stagePosition.x) / stageScale;
    const worldY = (pointer.y - stagePosition.y) / stageScale;
    const worldPoint = [worldX, worldY];

    if (activeTool === 'wall') {
      const snapped = currentFloor?.walls?.length
        ? snapToEndpoint(worldPoint, currentFloor.walls)
        : snapToGrid(worldPoint);

      if (!wallDrawStart) {
        setWallDrawStart(snapped);
        setWallDrawPreview(snapped);
      } else {
        if (distanceBetweenPoints(wallDrawStart, snapped) > 0.1) {
          const plans = clonePlans();
          const floor = plans.floor_plans[currentFloorIndex];
          if (!floor.walls) floor.walls = [];
          floor.walls.push({
            id: generateId('w'),
            start: wallDrawStart,
            end: snapped,
            type: 'interior',
            load_bearing: 'unknown',
            thickness_m: 0.15,
          });
          pushChange(plans);
        }
        setWallDrawStart(null);
        setWallDrawPreview(null);
      }
    } else if (activeTool === 'select') {
      handleDeselect();
    }
  }, [activeTool, wallDrawStart, stagePosition, stageScale, currentFloor, clonePlans, currentFloorIndex, pushChange, handleDeselect]);

  const handleStageMouseMove = useCallback((e) => {
    if (activeTool !== 'wall' || !wallDrawStart) return;
    const stage = stageRef.current;
    if (!stage) return;
    const pointer = stage.getPointerPosition();
    const worldX = (pointer.x - stagePosition.x) / stageScale;
    const worldY = (pointer.y - stagePosition.y) / stageScale;
    const snapped = currentFloor?.walls?.length
      ? snapToEndpoint([worldX, worldY], currentFloor.walls)
      : snapToGrid([worldX, worldY]);
    setWallDrawPreview(snapped);
  }, [activeTool, wallDrawStart, stagePosition, stageScale, currentFloor]);

  // ---------- Delete selected element ----------
  const deleteSelected = useCallback(() => {
    if (!selectedElementId || !selectedElementType) return;

    if (selectedElementType === 'wall') {
      const wall = currentFloor?.walls?.find((w) => w.id === selectedElementId);
      if (!wall || wall.load_bearing === 'yes') return;
      handleWallDelete(selectedElementId);
    } else if (selectedElementType === 'opening') {
      const plans = clonePlans();
      const floor = plans.floor_plans[currentFloorIndex];
      floor.openings = floor.openings?.filter((o) => o.id !== selectedElementId) || [];
      pushChange(plans);
      handleDeselect();
    }
  }, [selectedElementId, selectedElementType, currentFloor, handleWallDelete, clonePlans, currentFloorIndex, pushChange, handleDeselect]);

  // ---------- Keyboard shortcuts ----------
  useEffect(() => {
    const handler = (e) => {
      // Tool shortcuts (no modifier keys)
      if (!e.ctrlKey && !e.metaKey && !e.altKey) {
        switch (e.key) {
          case 'v': case 'V': setActiveTool('select'); return;
          case 'w': setActiveTool('wall'); return;
          case 'd': setActiveTool('door'); return;
          case 'o': setActiveTool('window'); return;
          case 'x': case 'X': setActiveTool('delete'); return;
          case 'c': case 'C': setShowCompliance(!showCompliance); return;
          case 'Escape':
            if (wallDrawStart) {
              setWallDrawStart(null);
              setWallDrawPreview(null);
            } else {
              handleDeselect();
            }
            return;
          case 'Delete': case 'Backspace':
            e.preventDefault();
            deleteSelected();
            return;
        }
      }

      // Undo: Ctrl/Cmd+Z
      if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        undo();
      }
      // Redo: Ctrl/Cmd+Shift+Z
      if ((e.ctrlKey || e.metaKey) && e.key === 'z' && e.shiftKey) {
        e.preventDefault();
        redo();
      }
      // Redo: Ctrl/Cmd+Y
      if ((e.ctrlKey || e.metaKey) && e.key === 'y') {
        e.preventDefault();
        redo();
      }
    };

    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [undo, redo, deleteSelected, handleDeselect, wallDrawStart]);

  // Clear wall drawing state when switching tools
  useEffect(() => {
    if (activeTool !== 'wall') {
      setWallDrawStart(null);
      setWallDrawPreview(null);
    }
  }, [activeTool]);

  // Zoom handler
  const handleWheel = useCallback((e) => {
    e.evt.preventDefault();
    const stage = stageRef.current;
    if (!stage) return;

    const pointer = stage.getPointerPosition();
    const oldScale = stage.scaleX();
    const scaleBy = 1.08;
    const newScale = e.evt.deltaY < 0 ? oldScale * scaleBy : oldScale / scaleBy;
    const clamped = Math.max(0.1, Math.min(200, newScale));

    const mousePointTo = {
      x: (pointer.x - stage.x()) / oldScale,
      y: (pointer.y - stage.y()) / oldScale,
    };

    setStageScale(clamped);
    setStagePosition({
      x: pointer.x - mousePointTo.x * clamped,
      y: pointer.y - mousePointTo.y * clamped,
    });
  }, []);

  const handleStageDragEnd = useCallback((e) => {
    setStagePosition({ x: e.target.x(), y: e.target.y() });
  }, []);

  // Canvas cursor
  const canvasCursor = useMemo(() => {
    if (activeTool === 'wall') return 'crosshair';
    if (activeTool === 'delete') return 'no-drop';
    if (activeTool === 'door' || activeTool === 'window') return 'copy';
    if (activeTool === 'room') return 'pointer';
    if (activeTool === 'measure') return 'crosshair';
    return 'grab';
  }, [activeTool]);

  // ---------- Drag and Drop functionality ----------
  const handleDragStart = (event) => {
    setActiveDragItem(event.active.data.current);
  };

  const handleDragEnd = (event) => {
    setActiveDragItem(null);
    const { over, active } = event;

    // Check if dropped over the stage area container
    if (!over || over.id !== 'floorplan-stage-container') return;

    const item = active.data.current;
    if (!item) return;

    // Calculate drop coordinates relative to stage layer
    const stage = stageRef.current;
    if (!stage) return;

    // Native event drop coordinates
    const dropPoint = {
      x: event.activatorEvent.clientX,
      y: event.activatorEvent.clientY,
    };

    // Convert client coordinate to stage world coordinate
    const stageBox = containerRef.current.getBoundingClientRect();
    const relativeX = dropPoint.x - stageBox.left;
    const relativeY = dropPoint.y - stageBox.top;

    const worldX = (relativeX - stagePosition.x) / stageScale;
    const worldY = (relativeY - stagePosition.y) / stageScale;

    const plans = clonePlans();
    const floor = plans.floor_plans[currentFloorIndex];
    if (!floor.rooms) floor.rooms = [];
    if (!floor.walls) floor.walls = [];
    if (!floor.openings) floor.openings = [];

    if (item.type === 'room') {
      // 1. Generate room and 4 walls
      const { room, walls } = generateRoomAndWalls(worldX, worldY, item.width, item.height, item.roomType, generateId);

      // 2. Add the room
      floor.rooms.push(room);

      // 3. Smart-merge walls 
      floor.walls = mergeOverlappingWalls(floor.walls, walls);

      pushChange(plans);
      setSelectedElementId(room.id);
      setSelectedElementType('room');
    }
    else if (item.type === 'opening') {
      // 1. Find nearest wall to drop point
      let nearestWall = null;
      let minDistance = Infinity;
      let projectedOffset = 0;

      for (const wall of floor.walls) {
        // Point-to-line segment distance and projection
        const px = worldX, py = worldY;
        const ax = wall.start[0], ay = wall.start[1];
        const bx = wall.end[0], by = wall.end[1];

        const L2 = (bx - ax) * (bx - ax) + (by - ay) * (by - ay);
        if (L2 === 0) continue;

        let t = ((px - ax) * (bx - ax) + (py - ay) * (by - ay)) / L2;
        let clampedT = Math.max(0.05, Math.min(0.95, t)); // Keep away from exact corners

        // Projected point on segment
        const projX = ax + clampedT * (bx - ax);
        const projY = ay + clampedT * (by - ay);

        const dist = distanceBetweenPoints([px, py], [projX, projY]);

        if (dist < minDistance && dist < 1.5) { // Must drop within 1.5 meters of a wall
          minDistance = dist;
          nearestWall = wall;
          projectedOffset = clampedT * Math.sqrt(L2);
        }
      }

      if (nearestWall) {
        const newOpening = {
          id: generateId('o'),
          type: item.openingType,
          wall_id: nearestWall.id,
          offset_along_wall: projectedOffset,
          width_m: item.width,
        };
        if (item.openingType === 'door') {
          newOpening.swing_direction = 'inward';
        }
        floor.openings.push(newOpening);
        pushChange(plans);
        setSelectedElementId(newOpening.id);
        setSelectedElementType('opening');
      }
    }
  };

  return (
    <DndContext sensors={sensors} onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
      <div className="floorplan-editor">
        {/* Toolbar - No Catalog */}
        <EditorToolbar
          activeTool={activeTool}
          onToolChange={setActiveTool}
          onUndo={undo}
          onRedo={redo}
          canUndo={historyIndex > 0}
          canRedo={historyIndex < editHistory.length - 1}
          showDimensions={showDimensions}
          onToggleDimensions={() => setShowDimensions(!showDimensions)}
        />

        {/* Center canvas */}
        <div
          className="floorplan-canvas"
          ref={containerRef}
          style={{ cursor: canvasCursor }}
        >
          <Stage
            ref={stageRef}
            width={stageSize.width}
            height={stageSize.height}
            scaleX={stageScale}
            scaleY={stageScale}
            x={stagePosition.x}
            y={stagePosition.y}
            draggable={activeTool === 'select' && !selectedElementId}
            onWheel={handleWheel}
            onDragEnd={handleStageDragEnd}
            onClick={handleStageClick}
            onTap={handleStageClick}
            onMouseMove={handleStageMouseMove}
          >
            <Layer>
              <RoomLayer
                rooms={currentFloor?.rooms}
                selectedId={selectedElementId}
                onSelect={handleSelectRoom}
                scale={stageScale}
                complianceResult={complianceResult}
                activeTool={activeTool}
              />
              <WallLayer
                walls={currentFloor?.walls}
                selectedId={selectedElementType === 'wall' ? selectedElementId : null}
                onSelect={handleSelectWall}
                scale={stageScale}
                activeTool={activeTool}
                onWallEndpointDrag={handleWallEndpointDrag}
                wallDragId={wallDragId}
                onWallCenterDragStart={handleWallCenterDragStart}
                onWallCenterDrag={handleWallCenterDrag}
                onWallCenterDragEnd={handleWallCenterDragEnd}
              />
              <OpeningLayer
                openings={currentFloor?.openings}
                walls={currentFloor?.walls}
                selectedId={selectedElementType === 'opening' ? selectedElementId : null}
                onSelect={handleSelectOpening}
                scale={stageScale}
                onOpeningDrag={handleOpeningDrag}
              />
              <DimensionLayer
                walls={currentFloor?.walls}
                rooms={currentFloor?.rooms}
                scale={stageScale}
                showDimensions={showDimensions}
              />
              <ComplianceBadgeLayer
                complianceResult={complianceResult}
                rooms={currentFloor?.rooms}
                walls={currentFloor?.walls}
                openings={currentFloor?.openings}
                scale={stageScale}
                selectedElementId={selectedElementId}
                onBadgeClick={(rule) => {
                  if (rule.element_id) {
                    setSelectedElementId(rule.element_id);
                    setSelectedElementType(rule.element_type || null);
                  }
                }}
              />

              {/* Wall drawing preview line */}
              {wallDrawStart && wallDrawPreview && (
                <>
                  <Line
                    points={[wallDrawStart[0], wallDrawStart[1], wallDrawPreview[0], wallDrawPreview[1]]}
                    stroke="#c8a55c"
                    strokeWidth={2 / stageScale}
                    dash={[6 / stageScale, 4 / stageScale]}
                    listening={false}
                  />
                  <Circle
                    x={wallDrawStart[0]}
                    y={wallDrawStart[1]}
                    radius={4 / stageScale}
                    fill="#c8a55c"
                    listening={false}
                  />
                  <Circle
                    x={wallDrawPreview[0]}
                    y={wallDrawPreview[1]}
                    radius={3 / stageScale}
                    fill="#c8a55c"
                    opacity={0.6}
                    listening={false}
                  />
                </>
              )}
            </Layer>
          </Stage>

          {/* Scale calibration modal */}
          {!scaleCalibrated && (
            <ScaleCalibration
              floorPlans={normalizedPlans}
              onCalibrate={(scaleData) => {
                setScaleCalibrated(true);
                if (normalizedPlans) {
                  const updated = { ...normalizedPlans, scale: scaleData };
                  pushChange(updated);
                }
              }}
              onSkip={() => setScaleCalibrated(true)}
            />
          )}

          {/* Room type popover */}
          {roomTypePopover && (
            <RoomTypeSelector
              currentType={roomTypePopover.currentType}
              position={roomTypePopover.position}
              onTypeChange={handleRoomTypeChange}
            />
          )}

          {/* Wall properties panel */}
          {selectedWall && (
            <WallProperties
              wall={selectedWall}
              onWallUpdate={handleWallUpdate}
              onWallDelete={handleWallDelete}
            />
          )}
        </div>

        {/* Right compliance panel - Collapsible */}
        {showCompliance && (
          <CompliancePanel
            complianceResult={complianceResult}
            selectedElementId={selectedElementId}
            onRuleClick={(elementId) => {
              setSelectedElementId(elementId);
              setSelectedElementType(null);
            }}
            loading={complianceLoading}
            onClose={() => setShowCompliance(false)}
          />
        )}

        {/* Compliance toggle button */}
        {!showCompliance && (
          <button
            className="compliance-toggle-btn"
            onClick={() => setShowCompliance(true)}
            title="Show Compliance Panel (C)"
          >
            ⚠️
          </button>
        )}
      </div>

      <DragOverlay dropAnimation={{ duration: 250, easing: 'cubic-bezier(0.18, 0.67, 0.6, 1.22)' }}>
        {activeDragItem ? (
          <div style={{
            opacity: 0.8,
            backgroundColor: activeDragItem.color ? `${activeDragItem.color}80` : '#ffffff80',
            border: `2px solid ${activeDragItem.color || '#333'}`,
            borderRadius: '4px',
            boxShadow: '0 8px 16px rgba(0,0,0,0.3)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            fontWeight: 'bold',
            textShadow: '0 1px 2px rgba(0,0,0,0.8)',
            width: activeDragItem.type === 'room' ? `${activeDragItem.width * stageScale}px` : '40px',
            height: activeDragItem.type === 'room' ? `${activeDragItem.height * stageScale}px` : '40px',
          }}>
            {activeDragItem.label}
          </div>
        ) : null}
      </DragOverlay>
    </DndContext>
  );
}
