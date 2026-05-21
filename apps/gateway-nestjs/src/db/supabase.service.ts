import { Injectable, OnModuleInit, Logger } from '@nestjs/common';
import { createClient, SupabaseClient } from '@supabase/supabase-js';

@Injectable()
export class SupabaseService implements OnModuleInit {
  private supabase: SupabaseClient;
  private readonly logger = new Logger(SupabaseService.name);

  onModuleInit() {
    const supabaseUrl = process.env.SUPABASE_URL;
    const supabaseKey = process.env.SUPABASE_KEY;

    if (!supabaseUrl || !supabaseKey) {
      this.logger.warn('SUPABASE_URL o SUPABASE_KEY no configurados. Usando placeholders de desarrollo.');
      this.supabase = createClient(
        'https://your-tenant.supabase.co',
        'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.dummykey'
      );
      return;
    }

    try {
      this.supabase = createClient(supabaseUrl, supabaseKey);
      this.logger.log('Cliente de Supabase inicializado correctamente.');
    } catch (e) {
      this.logger.error('Error al inicializar cliente de Supabase:', e);
    }
  }

  getClient(): SupabaseClient {
    return this.supabase;
  }
}
