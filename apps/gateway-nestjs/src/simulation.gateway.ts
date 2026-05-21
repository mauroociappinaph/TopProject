import { WebSocketGateway, WebSocketServer, SubscribeMessage, OnGatewayInit, OnGatewayConnection, OnGatewayDisconnect } from '@nestjs/websockets';
import { Logger } from '@nestjs/common';
import { Server, Socket } from 'socket.io';
import Redis from 'ioredis';

@WebSocketGateway({
  cors: {
    origin: '*',
  },
})
export class SimulationGateway implements OnGatewayInit, OnGatewayConnection, OnGatewayDisconnect {
  @WebSocketServer() server: Server;
  private logger: Logger = new Logger('SimulationGateway');
  private redisSub: Redis;

  afterInit(server: Server) {
    this.logger.log('WebSocket Gateway Inicializado correctamente.');
    
    // Conexión a Redis para Pub/Sub
    const redisHost = process.env.REDIS_HOST || 'localhost';
    const redisPort = parseInt(process.env.REDIS_PORT || '6379', 10);
    
    this.redisSub = new Redis({
      host: redisHost,
      port: redisPort,
    });

    // Suscripción al canal de simulación
    this.redisSub.subscribe('simulation:updates', (err, count) => {
      if (err) {
        this.logger.error('Error al suscribirse a Redis Pub/Sub:', err);
        return;
      }
      this.logger.log(`Suscrito a ${count} canales de Redis Pub/Sub.`);
    });

    // Recepción de mensajes desde FastAPI y retransmisión por WebSockets
    this.redisSub.on('message', (channel, message) => {
      if (channel === 'simulation:updates') {
        try {
          const data = JSON.parse(message);
          const roomName = `simulation:${data.simulation_id}`;
          
          this.logger.log(`Retransmitiendo evento de simulación a la sala ${roomName}: ${data.agent_name} -> ${data.action}`);
          
          // Emitir a la sala de WebSocket específica
          this.server.to(roomName).emit('agent:update', data);
        } catch (e) {
          this.logger.error('Error al deserializar mensaje de Redis:', e);
        }
      }
    });
  }

  handleConnection(client: Socket, ...args: any[]) {
    this.logger.log(`Cliente conectado: ${client.id}`);
  }

  handleDisconnect(client: Socket) {
    this.logger.log(`Cliente desconectado: ${client.id}`);
  }

  @SubscribeMessage('join:simulation')
  handleJoinRoom(client: Socket, simulationId: string): void {
    const roomName = `simulation:${simulationId}`;
    client.join(roomName);
    this.logger.log(`Cliente ${client.id} se unió a la sala ${roomName}`);
    client.emit('joined:room', { room: roomName });
  }
}
