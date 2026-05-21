import React, { useEffect, useRef, useState } from 'react';
import { io, Socket } from 'socket.io-client';

interface AgentUpdate {
  simulation_id: string;
  agent_name: string;
  action: string;
  coordinates: { x: number; y: number };
  extra: any;
}

export const ArenaSimulator: React.FC<{ simulationId: string }> = ({ simulationId }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [activeAgents, setActiveAgents] = useState<{ [key: string]: AgentUpdate }>({});
  const socketRef = useRef<Socket | null>(null);

  useEffect(() => {
    // 1. Conexión a Socket.io
    const gatewayUrl = process.env.NEXT_PUBLIC_GATEWAY_URL || 'http://localhost:3000';
    const socket = io(gatewayUrl);
    socketRef.current = socket;

    socket.on('connect', () => {
      console.log('Conectado al Gateway de NestJS por WebSockets');
      // Unirse a la sala específica de la simulación
      socket.emit('join:simulation', simulationId);
    });

    socket.on('agent:update', (data: AgentUpdate) => {
      // Registrar log local
      setLogs((prev) => [`[${data.agent_name}] ${data.action}`, ...prev.slice(0, 19)]);
      
      // Actualizar estado de agentes para renderizado React alternativo si Phaser está cargando
      setActiveAgents((prev) => ({
        ...prev,
        [data.agent_name]: data,
      }));
    });

    // 2. Carga dinámica de Phaser.js (Solo en el cliente)
    let game: any = null;
    import('phaser').then((Phaser) => {
      const config: import('phaser').Types.Core.GameConfig = {
        type: Phaser.AUTO,
        width: 800,
        height: 400,
        parent: containerRef.current || undefined,
        backgroundColor: '#0f172a', // Fondo pizarra oscuro moderno
        physics: {
          default: 'arcade',
          arcade: {
            gravity: { x: 0, y: 0 },
          },
        },
        scene: {
          preload: function(this: any) {
            // Placeholder de imagen para el agente
            this.load.image('agent_node', 'https://labs.phaser.io/assets/sprites/aqua_ball.png');
          },
          create: function(this: any) {
            this.agentSprites = {};
            this.add.text(10, 10, 'AgentArena 2D - Simulación en Tiempo Real', {
              fontFamily: 'Inter, system-ui, sans-serif',
              fontSize: '16px',
              color: '#38bdf8',
            });
            
            // Dibujar nodos estáticos en el mapa
            // Nodo Pinecone
            this.add.circle(100, 150, 15, 0x10b981);
            this.add.text(80, 175, 'Pinecone DB', { fontSize: '12px', color: '#10b981' });

            // Nodo Ollama
            this.add.circle(300, 200, 15, 0x8b5cf6);
            this.add.text(280, 225, 'Ollama Node', { fontSize: '12px', color: '#8b5cf6' });

            // Nodo Supervisor
            this.add.circle(500, 150, 15, 0xf59e0b);
            this.add.text(480, 175, 'Supervisor', { fontSize: '12px', color: '#f59e0b' });
          },
          update: function(this: any) {
            // Phaser interactúa con la reactividad escuchando actualizaciones directas
            socket.on('agent:update', (data: AgentUpdate) => {
              const spriteKey = data.agent_name;
              
              if (!this.agentSprites[spriteKey]) {
                // Crear avatar de agente si no existe
                const sprite = this.physics.add.sprite(data.coordinates.x, data.coordinates.y, 'agent_node');
                sprite.setScale(0.8);
                this.agentSprites[spriteKey] = sprite;
                
                // Texto superior flotante
                const label = this.add.text(data.coordinates.x - 20, data.coordinates.y - 25, data.agent_name, {
                  fontSize: '11px',
                  color: '#ffffff',
                });
                this.agentSprites[spriteKey + '_label'] = label;
              } else {
                // Animar movimiento del avatar al nuevo nodo
                this.tweens.add({
                  targets: this.agentSprites[spriteKey],
                  x: data.coordinates.x,
                  y: data.coordinates.y,
                  duration: 800,
                  ease: 'Power2',
                });
                this.tweens.add({
                  targets: this.agentSprites[spriteKey + '_label'],
                  x: data.coordinates.x - 20,
                  y: data.coordinates.y - 25,
                  duration: 800,
                  ease: 'Power2',
                });
              }
            });
          }
        }
      };

      game = new Phaser.Game(config);
    });

    return () => {
      socket.disconnect();
      if (game) {
        game.destroy(true);
      }
    };
  }, [simulationId]);

  return (
    <div className="flex flex-col gap-6 p-6 bg-slate-900 rounded-2xl border border-slate-800 shadow-2xl text-white">
      <div className="flex flex-col md:flex-row justify-between items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-sky-400 to-indigo-500">
            Simulador de la Arena Activo
          </h2>
          <p className="text-slate-400 text-sm">ID de Simulación: {simulationId}</p>
        </div>
        <div className="flex gap-2">
          <span className="flex h-3 w-3 relative">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
          </span>
          <span className="text-xs text-slate-400 font-medium">CONECTADO VIA WEBSOCKET</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Canvas de Phaser */}
        <div className="lg:col-span-2 overflow-hidden rounded-xl border border-slate-800 bg-slate-950 flex justify-center items-center">
          <div ref={containerRef} className="w-full h-[400px]" />
        </div>

        {/* Panel de Trazas y Logs */}
        <div className="bg-slate-950 rounded-xl p-4 border border-slate-800 flex flex-col h-[400px]">
          <h3 className="text-sm font-semibold tracking-wider text-slate-400 mb-3 uppercase">
            Trazas de Ejecución (MongoDB Logs)
          </h3>
          <div className="flex-1 overflow-y-auto space-y-2 pr-2 font-mono text-xs scrollbar-thin scrollbar-thumb-slate-800">
            {logs.length === 0 ? (
              <p className="text-slate-600 italic">Esperando que se inicie el flujo de agentes...</p>
            ) : (
              logs.map((log, index) => (
                <div key={index} className="p-2 rounded bg-slate-900 border-l-2 border-sky-500 text-sky-300">
                  {log}
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
