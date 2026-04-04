declare module 'node-mpv' {
  interface NodeMPVOptions {
    audio_only?: boolean;
    input_default_bindings?: boolean;
    terminal?: boolean;
  }

  interface MPVStatus {
    pause?: boolean;
    [key: string]: any;
  }

  interface MPVEvents {
    quit: () => void;
    crash: () => void;
    stopped: () => void;
    status: (status: MPVStatus) => void;
  }

  class NodeMPV {
    constructor(options?: NodeMPVOptions);
    start(): Promise<void>;
    loadfile(url: string): Promise<void>;
    pause(): Promise<void>;
    stop(): Promise<void>;
    volume(level: number): Promise<void>;
    quit(): Promise<void>;
    on<K extends keyof MPVEvents>(event: K, callback: MPVEvents[K]): void;
  }

  export default NodeMPV;
}
