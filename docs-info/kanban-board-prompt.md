# Kanban Board Implementation Prompt

## Overview
Create a fully functional Kanban board web application with real-time WebSocket data synchronization, with a functional chat panel sidebar. The application should display tasks as draggable cards grouped by status columns, with clickable cards that open modal popups showing detailed task information. The board should automatically update when data changes on the server.

## Layout Structure

### 1.1 Main Container Layout
- **Layout Ratio**: 1:5 split layout
  - **Left Panel (1/6 width)**: Chat panel or sidebar (conversational agent that has access to gemini pro)
  - **Right Panel (5/6 width)**: Kanban board area
- **Responsive Design**: 
  - On mobile/tablet: Stack vertically or use overlay for details panel
  - On desktop: Side-by-side layout with kanban board taking majority of space
- **Full Height**: Application should use full viewport height (`h-screen` or `100vh`)


# Page 1: Chat + Kanban Board

**Kanban Base**: Reuse Kanban code from `samples/kanban-frontend/src`

**Layout**:
```
┌───────────────────────────────────────────────────────┐
│  Vibe DevOps                            [Profile]     │
├──────────────┬────────────────────────────────────────┤
│              │  Kanban Board                          │
│  Chat        │  ┌────┬────┬──────┬────────┬──────┐    │
│  Interface   │  │Todo│Prog│Review│Deploying│Done │    │
│              │  ├────┴────┴──────┴────────┴──────┘    │
│  [Messages]  │  │  [Deployment Task Cards]            │
│              │  │                                     │
│  [Input]     │  │                                     │
│              │  │                                     │
│  [Agent      │  │                                     │
│   Status]    │  │                                     │
└──────────────┴────────────────────────────────────────┘
```

# Page 2: Architecture Dashboard
Leave that empty for now. we will build this later

### 1.2 Kanban Board Structure
```
┌─────────────────────────────────────────────────────────┐
│  Header/Navbar (optional)                                │
├─────────────────────────────────────────────────────────┤
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│  │ Column 1 │ │ Column 2 │ │ Column 3 │ │ Column 4 │ │
│  │ (Status) │ │ (Status) │ │ (Status) │ │ (Status) │ │
│  ├──────────┤ ├──────────┤ ├──────────┤ ├──────────┤ │
│  │  Card    │ │  Card    │ │  Card    │ │  Card    │ │
│  │  Card    │ │  Card    │ │  Card    │ │  Card    │ │
│  │  Card    │ │  Card    │ │  Card    │ │  Card    │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ │
└─────────────────────────────────────────────────────────┘
```

### 1.3 Component Hierarchy
```
Kanban App
├── LayoutContainer (1:5 ratio)
│   ├── LeftPanel (1/6 width) - Chat/Sidebar
│   └── RightPanel (5/6 width)
│       ├── KanbanBoardContainer
│       │   ├── KanbanProvider (DnD context)
│       │   │   ├── KanbanColumn (for each status)
│       │   │   │   ├── KanbanColumnHeader
│       │   │   │   │   ├── StatusLabel
│       │   │   │   │   ├── StatusColorIndicator
│       │   │   │   │   └── AddTaskButton (optional)
│       │   │   │   └── KanbanCardsContainer
│       │   │   │       └── TaskCard (for each task)
│       │   │   │           ├── TaskTitle
│       │   │   │           ├── TaskDescription (truncated)
│       │   │   │           └── TaskActionsMenu
│       └── TaskDetailsModal (conditional, overlay)
│           ├── ModalBackdrop
│           ├── ModalContent
│           │   ├── ModalHeader
│           │   │   ├── TaskTitle
│           │   │   └── CloseButton
│           │   ├── ModalBody
│           │   │   ├── TaskDetails
│           │   │   ├── SubtasksList
│           │   │   └── AdditionalInfo
│           │   └── ModalFooter (optional)
```

## Data Structure

### 2.1 Task Data Model
```typescript
interface Task {
  id: string;                    // Unique identifier
  title: string;                  // Task title (required)
  description?: string;           // Full task description
  status: TaskStatus;             // Current status (determines column)
  created_at: string;            // ISO timestamp
  updated_at: string;            // ISO timestamp
  subtasks?: Subtask[];          // Optional nested subtasks
  metadata?: Record<string, any>; // Additional custom fields
}

interface Subtask {
  id: string;
  title: string;
  description?: string;
  status: 'pending' | 'completed';
  task_id: string;               // Parent task ID
}

type TaskStatus = 
  | 'todo' 
  | 'inprogress' 
  | 'inreview' 
  | 'done' 
  | 'cancelled';
```

### 2.2 WebSocket Message Format
The WebSocket connection should use JSON Patch (RFC 6902) format for efficient updates:

**Initial Snapshot** (on connection):
```json
{
  "JsonPatch": [
    {
      "op": "replace",
      "path": "/tasks",
      "value": {
        "task-id-1": { /* full task object */ },
        "task-id-2": { /* full task object */ }
      }
    }
  ]
}
```

**Incremental Updates**:
```json
{
  "JsonPatch": [
    {
      "op": "add",
      "path": "/tasks/task-id-3",
      "value": { /* new task object */ }
    },
    {
      "op": "replace",
      "path": "/tasks/task-id-1/status",
      "value": "inprogress"
    },
    {
      "op": "remove",
      "path": "/tasks/task-id-2"
    }
  ]
}
```

**Connection Status Messages**:
```json
{ "finished": true }  // Server indicates stream is complete
```

### 2.3 Client State Structure
```typescript
interface TasksState {
  tasks: Record<string, Task>;  // Map of task ID -> Task object
}

// Derived data:
interface GroupedTasks {
  [status: TaskStatus]: Task[];  // Tasks grouped by status
}
```

## Functionality

### 3.1 WebSocket Connection & Data Sync

#### 3.1.1 Connection Management
- **Connection Endpoint**: `ws://localhost:PORT/api/tasks/stream/ws?project_id={projectId}`
  - Convert HTTP endpoint to WebSocket: `endpoint.replace(/^http/, 'ws')`
- **Connection Lifecycle**:
  1. Initialize empty state: `{ tasks: {} }`
  2. Establish WebSocket connection when component mounts
  3. On `onopen`: Set connection status to `connected`, reset retry attempts
  4. On `onmessage`: Parse JSON Patch messages and apply to state
  5. On `onerror`: Set error state, schedule reconnection
  6. On `onclose`: Schedule reconnection with exponential backoff

#### 3.1.2 Reconnection Strategy
- **Exponential Backoff**: 
  - Initial delay: 1 second
  - Max delay: 8 seconds
  - Formula: `Math.min(8000, 1000 * Math.pow(2, attempt))`
- **Retry Logic**:
  - Automatically retry on connection loss
  - Reset retry counter on successful connection
  - Show connection status indicator to user

#### 3.1.3 JSON Patch Application
- Use `rfc6902` library or similar to apply patches
- Deep clone state before applying patches (to trigger React re-renders)
- Apply patches in order as received
- Handle edge cases:
  - Invalid patch operations
  - Missing paths
  - Type mismatches

#### 3.1.4 State Updates
- Convert `Record<string, Task>` to array: `Object.values(tasks)`
- Sort tasks by `created_at` (newest first) or custom order
- Group tasks by status for column rendering
- Memoize grouped tasks to prevent unnecessary re-renders

### 3.2 Kanban Board Features

#### 3.2.1 Column Rendering
- Render one column per status type
- Column order: `['todo', 'inprogress', 'inreview', 'done', 'cancelled']`
- Each column shows:
  - **Header**: Status name, color indicator, task count (optional)
  - **Cards**: List of tasks with matching status
- Columns should be scrollable independently if content overflows

#### 3.2.2 Task Card Display
- **Card Content**:
  - Task title (required, truncated if too long)
  - Task description preview (first 130 characters, with ellipsis)
  - Visual indicators (optional):
    - Status badges
    - Priority indicators
    - Due date (if applicable)
- **Card Styling**:
  - Hover effects for interactivity
  - Selected/highlighted state when task details modal is open
  - Visual feedback during drag operations

#### 3.2.3 Drag and Drop
- **Library**: Use `@dnd-kit/core` or similar drag-and-drop library
- **Drag Activation**: 
  - Minimum drag distance: 8px (prevents accidental drags on clicks)
  - Use pointer sensor for mouse/touch support
- **Drop Zones**: Each status column is a droppable zone
- **Visual Feedback**:
  - Show drag preview while dragging
  - Highlight target column on hover
  - Show ghost/placeholder in original position
- **Drag End Handler**:
  - Extract dragged task ID and target status
  - Send update to server via REST API (not WebSocket for mutations)
  - WebSocket will receive update and refresh UI automatically
  - Handle errors: revert UI state if update fails

#### 3.2.4 Task Card Interactions
- **Click Handler**: Open task details modal
- **Context Menu** (optional): Right-click for quick actions
  - Edit task
  - Delete task
  - Duplicate task
- **Keyboard Navigation** (optional):
  - Arrow keys to navigate between cards
  - Enter to open details
  - Escape to close modal

### 3.3 Task Details Modal

#### 3.3.1 Modal Display
- **Trigger**: Click on any task card
- **Layout**: 
  - Overlay/backdrop (semi-transparent, clickable to close)
  - Centered or side panel modal
  - Responsive: full-screen on mobile, side panel on desktop
- **Animation**: Smooth fade-in/slide-in transition

#### 3.3.2 Modal Content
- **Header**:
  - Task title (editable, optional)
  - Close button (X icon)
  - Action buttons (Edit, Delete, etc.)
- **Body**:
  - Full task description
  - Task metadata (created date, updated date, etc.)
  - **Subtasks Section** (if applicable):
    - List of subtasks with checkboxes
    - Add new subtask input
    - Subtask status indicators
  - Additional fields from task metadata
- **Footer** (optional):
  - Save/Cancel buttons if editing
  - Additional actions

#### 3.3.3 Modal Interactions
- **Close Actions**:
  - Click backdrop
  - Click close button
  - Press Escape key
- **State Management**:
  - Track selected task ID
  - Fetch full task details if needed (or use data from WebSocket)
  - Update modal when task data changes via WebSocket

### 3.4 Real-time Updates

#### 3.4.1 Automatic UI Updates
- When WebSocket receives task updates:
  - Apply JSON Patch to state
  - React automatically re-renders affected components
  - Cards move between columns if status changes
  - Modal updates if currently viewing updated task
- **Optimistic Updates** (optional):
  - Update UI immediately on user actions
  - Revert if server rejects the change

#### 3.4.2 Update Scenarios
- **New Task Added**: Card appears in appropriate column
- **Task Status Changed**: Card moves to new column (with animation)
- **Task Updated**: Card content refreshes, modal updates if open
- **Task Deleted**: Card disappears, modal closes if viewing deleted task

## Error Handling

### 4.1 WebSocket Connection Errors

#### 4.1.1 Connection Failures
- **Initial Connection Failure**:
  - Show error message: "Failed to connect to server"
  - Display retry button
  - Show connection status indicator (disconnected icon)
- **Connection Lost**:
  - Show reconnecting indicator
  - Automatically attempt reconnection
  - Display message: "Reconnecting..." or "Connection lost, retrying..."

#### 4.1.2 Message Processing Errors
- **Invalid JSON**: Log error, skip message, continue listening
- **Invalid Patch**: Log error, show warning, continue with other patches
- **State Corruption**: Reset to last known good state, request full snapshot

### 4.2 Data Validation Errors

#### 4.2.1 Task Data Validation
- Validate required fields (id, title, status) before rendering
- Handle missing or malformed data gracefully
- Show placeholder for invalid tasks: "Invalid task data"

#### 4.2.2 Status Validation
- Validate status values against allowed list
- Default to 'todo' if status is invalid
- Log warnings for unexpected status values

### 4.3 User Action Errors

#### 4.3.1 Drag and Drop Errors
- **Update Failure**: 
  - Show error toast/notification
  - Revert card to original position
  - Display message: "Failed to update task status"
- **Network Error**:
  - Queue update for retry
  - Show offline indicator
  - Retry when connection restored

#### 4.3.2 Modal Errors
- **Task Not Found**: 
  - Close modal
  - Show error: "Task not found"
- **Load Failure**: 
  - Show error in modal
  - Provide retry button

### 4.4 Error UI Components
- **Connection Status Banner**: 
  - Green: Connected
  - Yellow: Reconnecting
  - Red: Disconnected
- **Error Toast/Notification**: 
  - Non-blocking error messages
  - Auto-dismiss after 5 seconds
  - Manual dismiss option

## User Flow

### 5.1 Application Initialization Flow

```
1. App Loads
   ↓
2. Initialize Empty State: { tasks: {} }
   ↓
3. Establish WebSocket Connection
   ↓
4. Show Loading State
   ↓
5. Receive Initial Snapshot (JSON Patch)
   ↓
6. Apply Patches to State
   ↓
7. Render Kanban Board with Tasks
   ↓
8. Show Connected Status
```

### 5.2 Task Interaction Flow

```
User Clicks Task Card
   ↓
Set Selected Task ID
   ↓
Open Task Details Modal
   ↓
Display Full Task Information
   ↓
[User Can:]
   - View Details
   - Edit Task (opens edit form)
   - Delete Task (shows confirmation)
   - Close Modal
```

### 5.3 Drag and Drop Flow

```
User Starts Dragging Card
   ↓
Show Drag Preview
   ↓
Highlight Target Column on Hover
   ↓
User Drops Card in New Column
   ↓
Extract: taskId, newStatus
   ↓
Send REST API Update: PATCH /api/tasks/{taskId}
   ↓
[Optimistic Update: Move Card Immediately]
   ↓
WebSocket Receives Status Update
   ↓
Apply JSON Patch to State
   ↓
UI Updates (Card Already in New Position)
```

### 5.4 Real-time Update Flow

```
Server Event Occurs (Task Created/Updated/Deleted)
   ↓
Server Sends JSON Patch via WebSocket
   ↓
Client Receives Message
   ↓
Parse JSON Patch
   ↓
Apply Patch to Current State
   ↓
React Re-renders Affected Components
   ↓
[If Modal Open for Updated Task]
   ↓
Update Modal Content
```

### 5.5 Connection Recovery Flow

```
Connection Lost
   ↓
Show "Reconnecting..." Indicator
   ↓
Schedule Reconnection (Exponential Backoff)
   ↓
Attempt Reconnection
   ↓
[Success]
   ↓
Reset Retry Counter
   ↓
Show "Connected" Status
   ↓
Receive Latest State via WebSocket
   ↓
[Failure]
   ↓
Increment Retry Counter
   ↓
Schedule Next Retry
   ↓
Repeat Until Connected
```

## Technical Implementation Details

### 6.1 Recommended Libraries
- **React**: UI framework
- **@dnd-kit/core**: Drag and drop functionality
- **rfc6902**: JSON Patch application
- **react-use-websocket** or native WebSocket API: WebSocket management
- **zustand** or **React Context**: State management
- **tailwindcss**: Styling (optional but recommended)

### 6.2 Key Hooks/Utilities

#### 6.2.1 WebSocket Hook
```typescript
function useTaskWebSocket(projectId: string) {
  // Returns: { tasks, tasksById, isLoading, isConnected, error }
  // Manages WebSocket connection, JSON Patch application, reconnection
}
```

#### 6.2.2 Task Grouping Hook
```typescript
function useGroupedTasks(tasks: Task[]) {
  // Returns: Record<TaskStatus, Task[]>
  // Groups tasks by status, memoized
}
```

### 6.3 Performance Optimizations
- **Memoization**: Memoize grouped tasks, filtered tasks
- **Virtual Scrolling**: For columns with many tasks (optional)
- **Debouncing**: Debounce rapid WebSocket updates if needed
- **Lazy Loading**: Load task details only when modal opens (if not in WebSocket stream)

### 6.4 Accessibility
- **Keyboard Navigation**: Full keyboard support for all interactions
- **ARIA Labels**: Proper labels for screen readers
- **Focus Management**: Manage focus when opening/closing modal
- **Color Contrast**: Ensure sufficient contrast for status indicators

## Status Configuration

### 7.1 Status Definitions
```typescript
const STATUS_CONFIG = {
  todo: {
    label: 'To Do',
    color: '--neutral-foreground', // or hex color
    order: 0
  },
  inprogress: {
    label: 'In Progress',
    color: '--info', // or blue
    order: 1
  },
  inreview: {
    label: 'In Review',
    color: '--warning', // or yellow
    order: 2
  },
  done: {
    label: 'Done',
    color: '--success', // or green
    order: 3
  },
  cancelled: {
    label: 'Cancelled',
    color: '--destructive', // or red
    order: 4
  }
};
```

## API Integration

### 8.1 REST API Endpoints (for mutations)
- `PATCH /api/tasks/{taskId}`: Update task (including status change)
- `POST /api/tasks`: Create new task
- `DELETE /api/tasks/{taskId}`: Delete task
- `GET /api/tasks/{taskId}`: Get single task (if needed for modal)

### 8.2 WebSocket Endpoint
- `ws://host/api/tasks/stream/ws?project_id={projectId}`
- Protocol: JSON Patch (RFC 6902)
- Messages: `{ "JsonPatch": [...] }` or `{ "finished": true }`

## Testing Considerations

### 9.1 Test Scenarios
- WebSocket connection establishment
- Initial data load
- Real-time updates (add, update, delete)
- Drag and drop status changes
- Modal open/close
- Connection loss and recovery
- Error handling
- Edge cases (empty state, single task, many tasks)

### 9.2 Mock Data
- Provide sample tasks for development
- Simulate WebSocket messages for testing
- Test with various status combinations

## UI/UX Guidelines

### 10.1 Visual Design
- **Modern, Clean Interface**: Use card-based design, subtle shadows
- **Color Coding**: Use status colors consistently
- **Spacing**: Adequate padding and margins for readability
- **Typography**: Clear hierarchy (title, description, metadata)

### 10.2 Animations
- **Smooth Transitions**: Card movements, modal open/close
- **Drag Feedback**: Visual feedback during drag operations
- **Status Changes**: Animate cards moving between columns

### 10.3 Responsive Behavior
- **Mobile**: Stack columns vertically or use horizontal scroll
- **Tablet**: 2-3 columns visible, horizontal scroll
- **Desktop**: All columns visible, side-by-side layout

## Summary

This prompt provides a comprehensive guide for building a Kanban board with:
- ✅ Real-time WebSocket synchronization using JSON Patch
- ✅ Drag-and-drop task management
- ✅ Clickable cards with detailed modal popups
- ✅ Automatic UI updates from server
- ✅ Robust error handling and reconnection
- ✅ Responsive 1:5 layout (chat panel:kanban board)
- ✅ Modern, accessible UI/UX

The implementation should prioritize real-time updates, smooth user interactions, and graceful error handling to create a production-ready Kanban board application.

