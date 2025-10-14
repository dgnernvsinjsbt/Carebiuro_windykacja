import { createClient } from '@/lib/supabase/server';
import type {
  MessageTemplate,
  TemplateChannel,
  TemplateKey,
  TemplateData,
  FormattedSMS,
  FormattedEmail,
  TemplatePlaceholder,
} from './types';
import { SMSFormatter } from './formatters/sms-formatter';
import { plainTextToHtml, plainTextToText } from '@/lib/email-formatter';

/**
 * Template Service
 * Central service for managing and formatting message templates
 */

export class TemplateService {
  /**
   * Gets a template by channel and key
   */
  static async getTemplate(
    channel: TemplateChannel,
    templateKey: TemplateKey
  ): Promise<MessageTemplate | null> {
    const supabase = await createClient();

    const { data, error } = await supabase
      .from('message_templates')
      .select('*')
      .eq('channel', channel)
      .eq('template_key', templateKey)
      .eq('is_active', true)
      .single();

    if (error) {
      console.error('Error fetching template:', error);
      return null;
    }

    return this.mapDatabaseToTemplate(data);
  }

  /**
   * Gets all templates for a channel
   */
  static async getTemplatesByChannel(
    channel: TemplateChannel
  ): Promise<MessageTemplate[]> {
    const supabase = await createClient();

    const { data, error } = await supabase
      .from('message_templates')
      .select('*')
      .eq('channel', channel)
      .eq('is_active', true)
      .order('template_key', { ascending: true });

    if (error) {
      console.error('Error fetching templates:', error);
      return [];
    }

    return data.map(this.mapDatabaseToTemplate);
  }

  /**
   * Gets a template by ID
   */
  static async getTemplateById(
    id: string
  ): Promise<MessageTemplate | null> {
    const supabase = await createClient();

    const { data, error } = await supabase
      .from('message_templates')
      .select('*')
      .eq('id', id)
      .single();

    if (error) {
      console.error('Error fetching template by ID:', error);
      return null;
    }

    return this.mapDatabaseToTemplate(data);
  }

  /**
   * Updates a template
   */
  static async updateTemplate(
    id: string,
    updates: Partial<MessageTemplate>
  ): Promise<{ success: boolean; error?: string }> {
    const supabase = await createClient();

    const { error } = await supabase
      .from('message_templates')
      .update({
        ...updates,
        updated_at: new Date().toISOString(),
      })
      .eq('id', id);

    if (error) {
      console.error('Error updating template:', error);
      return { success: false, error: error.message };
    }

    return { success: true };
  }

  /**
   * Formats a template with data
   */
  static async formatTemplate(
    channel: TemplateChannel,
    templateKey: TemplateKey,
    data: TemplateData
  ): Promise<FormattedEmail | FormattedSMS | null> {
    const template = await this.getTemplate(channel, templateKey);
    if (!template) return null;

    switch (channel) {
      case 'email':
        return this.formatEmailTemplate(template, data);
      case 'sms':
        return this.formatSMSTemplate(template, data);
      case 'whatsapp':
        return this.formatSMSTemplate(template, data); // WhatsApp uses same format as SMS
      default:
        return null;
    }
  }

  /**
   * Formats an email template
   */
  private static formatEmailTemplate(
    template: MessageTemplate,
    data: TemplateData
  ): FormattedEmail {
    let subject = template.subject || '';
    let bodyText = template.body_text || '';

    // Replace placeholders
    Object.entries(data).forEach(([key, value]) => {
      const placeholder = `{{${key}}}`;
      subject = subject.replace(new RegExp(placeholder, 'g'), value || '');
      bodyText = bodyText.replace(new RegExp(placeholder, 'g'), value || '');
    });

    // Convert to HTML and plain text
    const html = plainTextToHtml(bodyText);
    const text = plainTextToText(bodyText);

    return {
      subject,
      html,
      text,
    };
  }

  /**
   * Formats an SMS template
   */
  private static formatSMSTemplate(
    template: MessageTemplate,
    data: TemplateData
  ): FormattedSMS {
    const bodyText = template.body_text || '';
    return SMSFormatter.format(bodyText, data);
  }

  /**
   * Maps database row to MessageTemplate type
   */
  private static mapDatabaseToTemplate(data: any): MessageTemplate {
    return {
      id: data.id,
      channel: data.channel as TemplateChannel,
      template_key: data.template_key as TemplateKey,
      name: data.name,
      description: data.description,
      is_active: data.is_active,
      subject: data.subject,
      body_html: data.body_html,
      body_text: data.body_text,
      body_top: data.body_top,
      body_bottom: data.body_bottom,
      placeholders: (data.placeholders || []) as TemplatePlaceholder[],
      created_at: data.created_at,
      updated_at: data.updated_at,
      created_by: data.created_by,
    };
  }

  /**
   * Creates a new template (admin function)
   */
  static async createTemplate(
    template: Omit<MessageTemplate, 'id' | 'created_at' | 'updated_at'>
  ): Promise<{ success: boolean; id?: string; error?: string }> {
    const supabase = await createClient();

    const { data, error } = await supabase
      .from('message_templates')
      .insert({
        channel: template.channel,
        template_key: template.template_key,
        name: template.name,
        description: template.description,
        is_active: template.is_active,
        subject: template.subject,
        body_html: template.body_html,
        body_text: template.body_text,
        body_top: template.body_top,
        body_bottom: template.body_bottom,
        placeholders: template.placeholders,
        created_by: template.created_by,
      })
      .select('id')
      .single();

    if (error) {
      console.error('Error creating template:', error);
      return { success: false, error: error.message };
    }

    return { success: true, id: data.id };
  }

  /**
   * Deactivates a template (soft delete)
   */
  static async deactivateTemplate(
    id: string
  ): Promise<{ success: boolean; error?: string }> {
    const supabase = await createClient();

    const { error } = await supabase
      .from('message_templates')
      .update({ is_active: false })
      .eq('id', id);

    if (error) {
      console.error('Error deactivating template:', error);
      return { success: false, error: error.message };
    }

    return { success: true };
  }

  /**
   * Gets template version history
   */
  static async getTemplateVersions(templateId: string) {
    const supabase = await createClient();

    const { data, error } = await supabase
      .from('message_template_versions')
      .select('*')
      .eq('template_id', templateId)
      .order('version_number', { ascending: false });

    if (error) {
      console.error('Error fetching template versions:', error);
      return [];
    }

    return data;
  }
}
