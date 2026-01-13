# SafeVision System Flowchart

Here is the visual representation of the detection and alert logic.

```mermaid
flowchart TD
    %% Define Styles
    classDef start fill:#00f2ff,stroke:#000,stroke-width:2px,color:#000,rx:10,ry:10;
    classDef process fill:#1e293b,stroke:#3b82f6,stroke-width:2px,color:#fff;
    classDef decision fill:#f59e0b,stroke:#000,stroke-width:2px,color:#000,shape:diamond;
    classDef alert fill:#ef4444,stroke:#7f1d1d,stroke-width:4px,color:#fff,rx:5,ry:5;
    classDef subproc fill:#334155,stroke:#94a3b8,stroke-width:1px,color:#fff,stroke-dasharray: 5 5;

    %% Nodes
    Start([Camera Feed Input]):::start
    TamperCheck{Cam Tampered? \n(Dark/Blocked)}:::decision
    
    subgraph DetectionLoop [Active Monitoring Loop]
        direction TB
        ProcessFrame[Process Video Frame]:::process
        CheckMode{System Armed?}:::decision
        
        subgraph ModeChecks [Arming Protocols]
            AwayCheck(Away Mode Active?):::subproc
            NightCheck(Night Mode Active? \n12AM - 5AM):::subproc
        end
        
        IsolateROI[Isolate Monitoring Zones]:::process
        YOLO[Run YOLOv8 AI Model]:::process
        PersonFound{Person Detected?}:::decision
        
        subgraph verification [Smart Verification Protocol]
            StartTimer[Start/Resume 2s Timer]:::process
            CheckDuration{Persisted > 2 sec?}:::decision
            ResetTimer[Reset Timer]:::subproc
        end
    end

    TriggerAlert[TRIGGER INTRUDER ALERT]:::alert
    TriggerTamper[TRIGGER TAMPER ALERT]:::alert
    NotifyUser[Notify User / Web Interface]:::process
    Escalation{User Response?}:::decision
    Emergency[Contact Emergency Services]:::alert
    Dismiss[Alert Dismissed]:::process

    %% Connections
    Start --> ProcessFrame
    ProcessFrame --> TamperCheck
    
    TamperCheck -- Yes --> TriggerTamper
    TamperCheck -- No --> CheckMode
    
    CheckMode -- Check Config --> AwayCheck
    AwayCheck -- No --> NightCheck
    NightCheck -- No --> ProcessFrame
    
    AwayCheck -- Yes --> IsolateROI
    NightCheck -- Yes --> IsolateROI
    
    IsolateROI --> YOLO
    YOLO --> PersonFound
    
    PersonFound -- No --> ResetTimer
    ResetTimer --> ProcessFrame
    
    PersonFound -- Yes --> StartTimer
    StartTimer --> CheckDuration
    
    CheckDuration -- No (Analyzing...) --> ProcessFrame
    CheckDuration -- Yes (Confirmed) --> TriggerAlert
    
    TriggerAlert --> NotifyUser
    TriggerTamper --> NotifyUser
    
    NotifyUser --> Escalation
    Escalation -- No Response --> Emergency
    Escalation -- Manual Dismiss --> Dismiss
    Dismiss --> ProcessFrame

```

## Legend
- **<span style="color:#00f2ff">Cyan (Oval)</span>**: Start / Input
- **<span style="color:#f59e0b">Orange (Rhombus)</span>**: Decision Point (Yes/No)
- **<span style="color:#3b82f6">Dark Blue (Rect)</span>**: Processing Step
- **<span style="color:#ef4444">Red (Rect)</span>**: Critical Alert / Action
