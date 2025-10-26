import pandas as pd
from datetime import datetime
import os
from services.database import db

class ExcelExporter:
    def __init__(self):
        self.export_dir = "exports"
        if not os.path.exists(self.export_dir):
            os.makedirs(self.export_dir)

    def generate_full_report(self):
        """Генерация полного отчета в Excel с несколькими листами"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"bot_statistics_{timestamp}.xlsx"
        filepath = os.path.join(self.export_dir, filename)
        
        try:
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # Лист 1: Пользователи
                self._export_users(writer)
                
                # Лист 2: Рассылки
                self._export_mailings(writer)
                
                # Лист 3: Статистика рассылок
                self._export_mailing_stats(writer)
                
                # Лист 4: Общая статистика
                self._export_detailed_stats(writer)
                
                # Лист 5: Активность пользователей
                self._export_user_activity(writer)
            
            return filepath
        except Exception as e:
            print(f"Ошибка при генерации отчета: {e}")
            return None

    def _export_users(self, writer):
        """Экспорт данных пользователей"""
        try:
            users = db.get_all_users()
            users_data = []
            
            for user in users:
                users_data.append({
                    'ID': user.id,
                    'User ID': user.user_id,
                    'Username': user.username or 'Нет',
                    'Full Name': user.full_name or 'Без имени',
                    'Active': 'Да' if user.is_active else 'Нет',
                    'Joined': user.joined_at.strftime('%Y-%m-%d %H:%M') if user.joined_at else 'Неизвестно',
                    'Last Activity': user.last_activity.strftime('%Y-%m-%d %H:%M') if user.last_activity else 'Никогда',
                    'Days Since Join': (datetime.now() - user.joined_at).days if user.joined_at else 0
                })
            
            if users_data:
                df = pd.DataFrame(users_data)
                df.to_excel(writer, sheet_name='Пользователи', index=False)
                
                # Форматирование
                worksheet = writer.sheets['Пользователи']
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
        except Exception as e:
            print(f"Ошибка при экспорте пользователей: {e}")

    def _export_mailings(self, writer):
        """Экспорт данных рассылок"""
        try:
            mailings = db.get_all_mailings()
            mailings_data = []
            
            for mailing in mailings:
                stats = db.get_mailing_stats(mailing['id'])
                mailings_data.append({
                    'ID': mailing['id'],
                    'Title': mailing['title'],
                    'Type': mailing['message_type'],
                    'Status': mailing['status'],
                    'Created': mailing['created_at'].strftime('%Y-%m-%d %H:%M') if mailing['created_at'] else '',
                    'Text Length': len(mailing['message_text'] or ''),
                    'Has Media': 'Да' if mailing['media_file_id'] else 'Нет',
                    'Total Sent': stats['total_sent'],
                    'Delivered': stats['delivered'],
                    'Read': stats['read'],
                    'Success Rate': f"{stats['success_rate']:.1f}%"
                })
            
            if mailings_data:
                df = pd.DataFrame(mailings_data)
                df.to_excel(writer, sheet_name='Рассылки', index=False)
                
                # Форматирование
                worksheet = writer.sheets['Рассылки']
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
        except Exception as e:
            print(f"Ошибка при экспорте рассылок: {e}")

    def _export_mailing_stats(self, writer):
        """Экспорт статистики рассылок"""
        try:
            mailings = db.get_all_mailings()
            stats_data = []
            
            for mailing in mailings:
                stats = db.get_mailing_stats(mailing['id'])
                total_sent = stats['total_sent']
                delivered = stats['delivered']
                read_count = stats['read']
                
                delivery_rate = (delivered/total_sent*100) if total_sent > 0 else 0
                read_rate = (read_count/total_sent*100) if total_sent > 0 else 0
                
                stats_data.append({
                    'Mailing ID': mailing['id'],
                    'Title': mailing['title'],
                    'Status': mailing['status'],
                    'Total Sent': total_sent,
                    'Delivered': delivered,
                    'Read': read_count,
                    'Delivery Rate': f"{delivery_rate:.1f}%",
                    'Read Rate': f"{read_rate:.1f}%",
                    'Success Rate': f"{stats['success_rate']:.1f}%",
                    'Created': mailing['created_at'].strftime('%Y-%m-%d') if mailing['created_at'] else ''
                })
            
            if stats_data:
                df = pd.DataFrame(stats_data)
                df.to_excel(writer, sheet_name='Статистика рассылок', index=False)
                
                # Форматирование
                worksheet = writer.sheets['Статистика рассылок']
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 30)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
        except Exception as e:
            print(f"Ошибка при экспорте статистики рассылок: {e}")

    def _export_detailed_stats(self, writer):
        """Экспорт детальной статистики"""
        try:
            # Общая статистика
            total_users = db.get_user_count()
            active_today = db.get_active_users_count_today()
            active_week = db.get_active_users_count_week()
            new_today = db.get_new_users_count(days=1)
            new_week = db.get_new_users_count(days=7)
            
            # Статистика по рассылкам
            all_mailings = db.get_all_mailings()
            active_mailings = db.get_mailings_by_status('active')
            draft_mailings = db.get_mailings_by_status('draft')
            archived_mailings = db.get_mailings_by_status('archived')
            
            summary_data = [{
                'Metric': 'Total Users',
                'Value': total_users,
                'Description': 'Всего пользователей'
            }, {
                'Metric': 'Active Today',
                'Value': active_today,
                'Description': 'Активных сегодня'
            }, {
                'Metric': 'Active Week',
                'Value': active_week,
                'Description': 'Активных за неделю'
            }, {
                'Metric': 'New Today',
                'Value': new_today,
                'Description': 'Новых сегодня'
            }, {
                'Metric': 'New Week',
                'Value': new_week,
                'Description': 'Новых за неделю'
            }, {
                'Metric': 'Total Mailings',
                'Value': len(all_mailings),
                'Description': 'Всего рассылок'
            }, {
                'Metric': 'Active Mailings',
                'Value': len(active_mailings),
                'Description': 'Активных рассылок'
            }, {
                'Metric': 'Draft Mailings',
                'Value': len(draft_mailings),
                'Description': 'Черновиков'
            }, {
                'Metric': 'Archived Mailings',
                'Value': len(archived_mailings),
                'Description': 'В архиве'
            }]
            
            df_summary = pd.DataFrame(summary_data)
            df_summary.to_excel(writer, sheet_name='Общая статистика', index=False)
            
            # Форматирование
            worksheet = writer.sheets['Общая статистика']
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 30)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        except Exception as e:
            print(f"Ошибка при экспорте детальной статистики: {e}")

    def _export_user_activity(self, writer):
        """Экспорт активности пользователей"""
        try:
            users = db.get_all_users()
            activity_data = []
            
            for user in users:
                days_since_join = (datetime.now() - user.joined_at).days if user.joined_at else 0
                days_since_activity = (datetime.now() - user.last_activity).days if user.last_activity else 999
                
                activity_data.append({
                    'User ID': user.user_id,
                    'Username': user.username or 'Нет',
                    'Full Name': user.full_name or 'Без имени',
                    'Joined': user.joined_at.strftime('%Y-%m-%d') if user.joined_at else 'Неизвестно',
                    'Last Activity': user.last_activity.strftime('%Y-%m-%d %H:%M') if user.last_activity else 'Никогда',
                    'Days Since Join': days_since_join,
                    'Days Since Activity': days_since_activity,
                    'Status': 'Active' if user.is_active else 'Inactive',
                    'Activity Level': self._get_activity_level(days_since_activity)
                })
            
            if activity_data:
                df = pd.DataFrame(activity_data)
                df.to_excel(writer, sheet_name='Активность пользователей', index=False)
                
                # Форматирование
                worksheet = writer.sheets['Активность пользователей']
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 25)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
        except Exception as e:
            print(f"Ошибка при экспорте активности пользователей: {e}")

    def _get_activity_level(self, days_since_activity):
        """Определение уровня активности"""
        if days_since_activity == 999:
            return 'Never'
        elif days_since_activity == 0:
            return 'Today'
        elif days_since_activity <= 1:
            return 'Very High'
        elif days_since_activity <= 3:
            return 'High'
        elif days_since_activity <= 7:
            return 'Medium'
        elif days_since_activity <= 30:
            return 'Low'
        else:
            return 'Inactive'

    def cleanup_old_exports(self, keep_last_n=10):
        """Удаление старых экспортов, оставляя только последние N файлов"""
        try:
            files = [os.path.join(self.export_dir, f) for f in os.listdir(self.export_dir) 
                    if f.startswith('bot_statistics_') and f.endswith('.xlsx')]
            
            # Сортируем по времени изменения (новые сначала)
            files.sort(key=os.path.getmtime, reverse=True)
            
            # Удаляем старые файлы
            for file_to_delete in files[keep_last_n:]:
                os.remove(file_to_delete)
                print(f"Удален старый файл экспорта: {file_to_delete}")
                
        except Exception as e:
            print(f"Ошибка при очистке старых экспортов: {e}")