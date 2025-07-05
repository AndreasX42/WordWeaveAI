import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';

export interface Language {
  code: string;
  name: string;
  flag: string;
}

@Injectable({
  providedIn: 'root',
})
export class TranslationService {
  private http = inject(HttpClient);

  private readonly LANGUAGE_STORAGE_KEY = 'language';

  // Available languages
  readonly languages: Language[] = [
    { code: 'en', name: 'English', flag: '🇺🇸' },
    { code: 'es', name: 'Español', flag: '🇪🇸' },
    { code: 'de', name: 'Deutsch', flag: '🇩🇪' },
  ];

  // Current language signal
  private currentLanguageSignal = signal<Language>(this.languages[0]); // English default

  // Translation cache
  private translationCache = new Map<string, Record<string, unknown>>();

  constructor() {
    // Load saved language preference
    const savedLanguage = localStorage.getItem(this.LANGUAGE_STORAGE_KEY);
    if (savedLanguage) {
      const language = this.languages.find((l) => l.code === savedLanguage);
      if (language) {
        this.currentLanguageSignal.set(language);
      }
    }

    // Load initial translations
    this.loadTranslations(this.currentLanguageSignal().code);
  }

  // Get current language signal
  getCurrentLanguage() {
    return this.currentLanguageSignal.asReadonly();
  }

  // Change language
  changeLanguage(languageCode: string): void {
    const language = this.languages.find((l) => l.code === languageCode);
    if (language) {
      this.currentLanguageSignal.set(language);
      localStorage.setItem(this.LANGUAGE_STORAGE_KEY, languageCode);
      this.loadTranslations(languageCode);
    }
  }

  // Load translations for a specific language
  private loadTranslations(languageCode: string): void {
    if (this.translationCache.has(languageCode)) {
      return;
    }

    const translations = this.getTranslations(languageCode);
    this.translationCache.set(languageCode, translations);
  }

  // Get translation for a key
  translate(key: string, params?: Record<string, string>): string {
    const currentLang = this.currentLanguageSignal().code;
    const translations = this.translationCache.get(currentLang) || {};

    let translation = this.getNestedTranslation(translations, key) || key;

    // Replace parameters if provided
    if (params) {
      Object.keys(params).forEach((paramKey) => {
        translation = translation.replace(`{{${paramKey}}}`, params[paramKey]);
      });
    }

    return translation;
  }

  // Get nested translation from object
  private getNestedTranslation(
    obj: Record<string, unknown>,
    key: string
  ): string | null {
    return key.split('.').reduce((o, i) => {
      if (o && typeof o === 'object' && i in o) {
        return (o as Record<string, unknown>)[i];
      }
      return undefined;
    }, obj as unknown) as string | null;
  }

  // Get translations for a language
  private getTranslations(languageCode: string): Record<string, unknown> {
    const translations = {
      en: {
        header: {
          search: 'Search',
          notifications: 'Notifications',
          account: 'Account',
          profile: 'Profile',
          language: 'Language',
          lightMode: 'Light Mode',
          darkMode: 'Dark Mode',
          healthDashboard: 'Health Dashboard',
          signIn: 'Sign In',
          signOut: 'Sign Out',
          register: 'Register',
          guestUser: 'Guest User',
          notSignedIn: 'Not Signed In',
        },
        common: {
          welcome: 'Welcome',
          home: 'Home',
          loading: 'Loading…',
          error: 'Error',
          success: 'Success',
          cancel: 'Cancel',
          confirm: 'Confirm',
          save: 'Save',
          edit: 'Edit',
          delete: 'Delete',
          close: 'Close',
        },
        messages: {
          unknownError: 'Something went wrong. Please try again.',
          loginCredentialsIncorrect:
            'Invalid username or password. Please check your credentials and try again.',
          networkError:
            'Network error. Please check your connection and try again.',
          serverError: 'Server error. Please try again later.',
          loginFirst: 'Please sign in to continue.',
          sessionExpired: 'Your session has expired. Please sign in again.',
        },
        health: {
          dashboard: {
            title: 'Health Dashboard',
            refresh: 'Refresh',
            lastUpdated: 'Last Updated',
            status: {
              excellent: 'Excellent',
              good: 'Good',
              poor: 'Poor',
            },
            tiles: {
              backendHealth: 'Backend Health',
              backendHealthDescription: 'Backend API uptime & error rate',
              backendResponseTime: 'Response Time',
              backendResponseTimeDescription: 'Average API response time',
              backendErrorRate: 'Error Rate',
              backendErrorRateDescription: 'Backend errors per minute',
              jsErrorRate: 'JS Error Rate',
              jsErrorRateDescription: 'JavaScript errors per minute',
            },
            values: {
              offline: 'Offline',
              noErrors: 'No Errors',
              errorsPerMinute: 'errors/min',
              milliseconds: 'ms',
            },
          },
        },
        auth: {
          // Page titles and headers
          signIn: 'Sign In',
          signInSubtitle: 'Welcome back! Sign in to your account.',
          createAccount: 'Create Account',
          createAccountSubtitle: 'Create your account to get started!',
          resetPassword: 'Reset Password',
          resetPasswordSubtitle:
            'Enter your email address to reset your password.',
          verifyEmail: 'Verify Email',
          verifyEmailSubtitle: "We've sent a verification code to {{email}}",
          userProfile: 'User Profile',

          // Form labels
          username: 'Username',
          emailAddress: 'Email Address',
          password: 'Password',
          confirmPassword: 'Confirm Password',
          verificationCode: 'Verification Code',

          // Placeholders
          enterEmail: 'Enter your email address',
          enterPassword: 'Enter your password',
          enterUsername: 'Enter your username',
          confirmYourPassword: 'Confirm your password',
          enterVerificationCode: 'Enter 6-digit code',

          // Button labels
          signInButton: 'Sign In',
          signingIn: 'Signing In…',
          createAccountButton: 'Create Account',
          creatingAccount: 'Creating Account…',
          resetPasswordButton: 'Reset Password',
          sending: 'Sending…',
          verifyEmailButton: 'Verify Email',
          verifying: 'Verifying…',
          resendCode: 'Resend Code',
          resendingCode: 'Resending…',
          resendInTime: 'Resend in {{time}}',
          backToLogin: 'Back to Sign In',
          updateAccount: 'Update Account',
          updateAccountButton: 'Update Account',
          updatingAccount: 'Updating…',
          deleteAccount: 'Delete Account',

          // Links and navigation
          dontHaveAccount: "Don't have an account?",
          createAccountLink: 'Create account',
          alreadyHaveAccount: 'Already have an account?',
          signInLink: 'Sign in',
          forgotPasswordLink: 'Forgot your password?',
          didntReceiveCode: "Didn't receive the code?",

          // Google OAuth
          continueWithGoogle: 'Continue with Google',
          or: 'or',

          // Profile page
          manageAccount: 'Manage your account settings and preferences',
          accountInformation: 'Account Information',
          notAvailable: 'Not available',
          emailStatus: 'Email Status',
          verified: 'Verified',
          notVerified: 'Not Verified',
          role: 'Role',
          sessionStatus: 'Session Status',
          sessionExpiresIn: 'Session Expires In',
          sessionExpired: 'Session Expired',
          noSession: 'No Session',
          invalidSession: 'Invalid Session',
          preferences: 'Preferences',
          darkMode: 'Dark Mode',
          darkModeDescription: 'Switch between light and dark themes',
          accountActions: 'Account Actions',
          signOut: 'Sign Out',

          // Success states
          emailSentSuccessfully: 'Email Sent Successfully!',
          checkYourEmail: 'Check your email!',
          newPasswordSent: "We've sent you a new password.",
          emailSentIfExists:
            "If an account with that email exists, you'll receive password reset instructions shortly.",

          // Success messages
          loginSuccessful: 'Login successful!',
          registrationSuccessful:
            'Registration successful! Please check your email for verification code.',
          emailVerifiedSuccessfully: 'Email verified successfully!',
          verificationCodeResent: 'Verification code resent to your email.',
          logoutSuccessful: 'Logout successful!',
          accountDeletedSuccessfully: 'Account deleted successfully!',
          updateAccountSuccess: 'Account updated successfully!',

          // Error messages
          invalidCredentials: 'Invalid credentials. Please try again.',
          loginFailed: 'Login failed. Please try again.',
          unexpectedError: 'An unexpected error occurred. Please try again.',
          emailNotVerified:
            'Please verify your email address before signing in.',
          googleLoginFailed:
            'Failed to initiate Google login. Please try again.',
          registrationFailed: 'Registration failed. Please try again.',
          usernameOrEmailExists:
            'Username or email already exists. Please try different credentials.',
          resetEmailFailed: 'Failed to send reset email. Please try again.',
          verificationFailed: 'Verification failed. Please try again.',
          invalidVerificationCode:
            'Invalid verification code. Please try again.',
          resendCodeFailed: 'Failed to resend code. Please try again.',
          logoutFailed: 'Logout failed!',
          accountDeletionFailed: 'Account deletion failed. Please try again.',
          updateAccountFailed: 'Failed to update account. Please try again.',

          // Confirmation dialogs
          deleteAccountConfirm:
            'Are you sure you want to delete your account? This action cannot be undone.',

          // Accessibility labels
          showPassword: 'Show password',
          hidePassword: 'Hide password',
          resendVerificationCode: 'Resend verification code',

          // Optional field labels
          passwordOptional: 'Password (optional)',
        },
        home: {
          hero: {
            title: 'Build your vocabulary with',
            titleHighlight: 'AI-powered community learning',
            subtitle:
              'Create personalized vocabulary lists from our community database, or watch our AI Agents generate new words in real time with audio, images, and examples. Master any combination of English, Spanish, and German through interactive quizzes and collaborative learning.',
            ctaButton: 'Start building',
            stats: {
              wordsCreated: 'Words Created',
              publicLists: 'Public Lists',
              activeUsers: 'Active Users',
            },
          },
          howItWorks: {
            title: 'How WordWeave Works',
            subtitle: 'Community-driven vocabulary learning in 3 simple steps',
            step1: {
              title: 'Create Your Lists',
              description:
                'Build private or public vocabulary lists using words from our community database. Choose any source–target language combination between English, Spanish, and German.',
            },
            step2: {
              title: 'AI Creates Missing Words',
              description:
                "Need a word that doesn't exist yet? Watch our AI Agents generate comprehensive vocabulary cards in real time with audio, contextual images, and usage examples. Provide feedback to improve the results.",
            },
            step3: {
              title: 'Learn with Quizzes',
              description:
                'Test your knowledge with multiple-choice quizzes based on your personal vocabulary lists. Track your progress and master new languages effectively.',
            },
          },
          features: {
            title: 'Everything You Need to Master Vocabulary',
            subtitle: 'Powerful features for collaborative language learning',
            personalLists: {
              title: 'Personal & Public Lists',
              description:
                'Create private vocabulary lists for personal study or share public lists with the community. Organize words by theme, difficulty, or learning goal.',
            },
            communityDatabase: {
              title: 'Community Database',
              description:
                'Every word generated by our AI Agents becomes available to all users. Build on the work of others and contribute to a growing shared vocabulary resource.',
            },
            aiGeneration: {
              title: 'Real-time AI Generation',
              description:
                'Watch our AI Agents create vocabulary cards live with audio pronunciation, contextual images, and usage examples. Provide feedback to perfect each word.',
            },
          },
        },
        search: {
          title: 'Discover',
          titleHighlight: 'New Words',
          subtitle:
            'Search for words in our community database or let our AI Agents create them for you',
          sourceLanguage: 'From',
          targetLanguage: 'To',
          selectLanguage: 'Select Language',
          inputPlaceholder: 'Enter a word to search',
          button: 'Search',
        },
      },
      de: {
        header: {
          search: 'Suchen',
          notifications: 'Benachrichtigungen',
          account: 'Konto',
          profile: 'Profil',
          language: 'Sprache',
          lightMode: 'Heller Modus',
          darkMode: 'Dunkler Modus',
          healthDashboard: 'Health-Dashboard',
          signIn: 'Anmelden',
          signOut: 'Abmelden',
          register: 'Registrieren',
          guestUser: 'Gast',
          notSignedIn: 'Nicht angemeldet',
        },
        common: {
          welcome: 'Willkommen',
          home: 'Startseite',
          loading: 'Lädt…',
          error: 'Fehler',
          success: 'Erfolgreich',
          cancel: 'Abbrechen',
          confirm: 'Bestätigen',
          save: 'Speichern',
          edit: 'Bearbeiten',
          delete: 'Löschen',
          close: 'Schließen',
        },
        messages: {
          unknownError:
            'Da ist etwas schiefgelaufen. Bitte versuche es erneut.',
          loginCredentialsIncorrect:
            'Ungültiger Benutzername oder Passwort. Bitte prüfe deine Daten und probiere es noch einmal.',
          networkError:
            'Netzwerkfehler. Bitte überprüfe deine Verbindung und versuche es erneut.',
          serverError: 'Serverfehler. Bitte später noch einmal versuchen.',
          loginFirst: 'Bitte melde dich zuerst an, um weiterzumachen.',
          sessionExpired:
            'Deine Sitzung ist abgelaufen. Bitte melde dich erneut an.',
        },
        health: {
          dashboard: {
            title: 'Health-Dashboard',
            refresh: 'Aktualisieren',
            lastUpdated: 'Zuletzt aktualisiert',
            status: {
              excellent: 'Sehr gut',
              good: 'Gut',
              poor: 'Schwach',
            },
            tiles: {
              backendHealth: 'Backend-Status',
              backendHealthDescription: 'Uptime & Fehler des Backends',
              backendResponseTime: 'Antwortzeit',
              backendResponseTimeDescription: 'Durchschnittliche API-Latenz',
              backendErrorRate: 'Fehlerquote',
              backendErrorRateDescription: 'Fehler pro Minute',
              jsErrorRate: 'JS-Fehlerquote',
              jsErrorRateDescription: 'JS-Fehler pro Minute',
            },
            values: {
              offline: 'Offline',
              noErrors: 'Keine Fehler',
              errorsPerMinute: 'Fehler/min',
              milliseconds: 'ms',
            },
          },
        },
        auth: {
          signIn: 'Anmelden',
          signInSubtitle: 'Schön, dass du da bist! Melde dich an.',
          createAccount: 'Konto erstellen',
          createAccountSubtitle: 'Lege jetzt dein Konto an!',
          resetPassword: 'Passwort zurücksetzen',
          resetPasswordSubtitle:
            'Gib deine E-Mail ein, um dein Passwort zurückzusetzen.',
          verifyEmail: 'E-Mail bestätigen',
          verifyEmailSubtitle:
            'Wir haben dir einen Code an {{email}} geschickt.',
          userProfile: 'Profil',

          username: 'Benutzername',
          email: 'E-Mail',
          emailAddress: 'E-Mail Adresse',
          password: 'Passwort',
          confirmPassword: 'Passwort bestätigen',
          verificationCode: 'Verifizierungscode',

          enterEmail: 'E-Mail eingeben',
          enterPassword: 'Passwort eingeben',
          enterUsername: 'Benutzernamen eingeben',
          confirmYourPassword: 'Passwort noch einmal eingeben',
          enterVerificationCode: '6-stelligen Code eingeben',

          signInButton: 'Anmelden',
          signingIn: 'Anmeldung…',
          createAccountButton: 'Konto erstellen',
          creatingAccount: 'Erstelle Konto…',
          resetPasswordButton: 'Link senden',
          sending: 'Senden…',
          verifyEmailButton: 'Bestätigen',
          verifying: 'Bestätige…',
          resendCode: 'Code erneut senden',
          resendingCode: 'Erneut senden…',
          resendInTime: 'Erneut senden in {{time}}',
          backToLogin: 'Zur Anmeldung',
          updateAccount: 'Konto aktualisieren',
          updateAccountButton: 'Aktualisieren',
          updatingAccount: 'Aktualisiere…',
          deleteAccount: 'Konto löschen',

          dontHaveAccount: 'Noch kein Konto?',
          createAccountLink: 'Konto erstellen',
          alreadyHaveAccount: 'Schon dabei?',
          signInLink: 'Anmelden',
          forgotPasswordLink: 'Passwort vergessen?',
          didntReceiveCode: 'Code nicht erhalten?',

          continueWithGoogle: 'Mit Google fortfahren',
          or: 'oder',

          manageAccount: 'Verwalte deine Einstellungen',
          accountInformation: 'Kontoinfos',
          notAvailable: 'Nicht verfügbar',
          emailStatus: 'E-Mail-Status',
          verified: 'Bestätigt',
          notVerified: 'Noch nicht bestätigt',
          role: 'Rolle',
          sessionStatus: 'Sitzung',
          sessionExpiresIn: 'Läuft ab in',
          sessionExpired: 'Abgelaufen',
          noSession: 'Keine Sitzung',
          invalidSession: 'Ungültige Sitzung',
          preferences: 'Einstellungen',
          darkMode: 'Dunkler Modus',
          darkModeDescription: 'Wechsle zwischen hell und dunkel',
          accountActions: 'Aktionen',
          signOut: 'Abmelden',

          emailSentSuccessfully: 'E-Mail erfolgreich gesendet!',
          checkYourEmail: 'Schau in dein Postfach!',
          newPasswordSent: 'Neues Passwort geschickt.',
          emailSentIfExists:
            'Falls du ein Konto hast, bekommst du gleich Anweisungen.',

          loginSuccessful: 'Angemeldet!',
          registrationSuccessful:
            'Registrierung erfolgreich! Check deine E-Mail.',
          emailVerifiedSuccessfully: 'E-Mail bestätigt!',
          verificationCodeResent: 'Code erneut gesendet.',
          logoutSuccessful: 'Abgemeldet!',
          accountDeletedSuccessfully: 'Konto gelöscht!',
          updateAccountSuccess: 'Aktualisiert!',

          invalidCredentials: 'Ungültige Daten. Versuch’s noch mal.',
          loginFailed: 'Anmeldung fehlgeschlagen. Versuch’s erneut.',
          unexpectedError: 'Unerwarteter Fehler. Versuch’s erneut.',
          emailNotVerified: 'Bitte bestätige zuerst deine E-Mail.',
          googleLoginFailed: 'Google-Login fehlgeschlagen.',
          registrationFailed: 'Registrierung fehlgeschlagen.',
          usernameOrEmailExists: 'Benutzername oder E-Mail schon vergeben.',
          resetEmailFailed: 'Link konnte nicht gesendet werden.',
          verificationFailed: 'Bestätigung fehlgeschlagen.',
          invalidVerificationCode: 'Ungültiger Code.',
          resendCodeFailed: 'Code konnte nicht gesendet werden.',
          logoutFailed: 'Abmeldung fehlgeschlagen.',
          accountDeletionFailed: 'Löschen fehlgeschlagen.',
          updateAccountFailed: 'Update fehlgeschlagen.',

          deleteAccountConfirm:
            'Willst du dein Konto wirklich löschen? Das kann nicht rückgängig gemacht werden.',

          showPassword: 'Passwort anzeigen',
          hidePassword: 'Passwort verbergen',
          resendVerificationCode: 'Verifizierungscode erneut senden',
          passwordOptional: 'Passwort (optional)',
        },
        home: {
          hero: {
            title: 'Erweitere deinen Wortschatz mit',
            titleHighlight: 'KI-gestütztem Community-Lernen',
            subtitle:
              'Erstelle individuelle Vokabellisten aus unserer Community-Datenbank oder sieh zu, wie unsere KI-Agenten in Echtzeit neue Wörter mit Audio, Bildern und Beispielen erzeugen. Meistere Englisch, Spanisch und Deutsch dank interaktiver Quizze und gemeinsamer Lernerfahrung.',
            ctaButton: 'Jetzt loslegen',
            stats: {
              wordsCreated: 'Wörter erstellt',
              publicLists: 'Öffentliche Listen',
              activeUsers: 'Aktive Nutzer',
            },
          },
          howItWorks: {
            title: 'So funktioniert WordWeave',
            subtitle: 'Community-basiertes Vokabellernen in 3 Schritten',
            step1: {
              title: 'Deine Listen erstellen',
              description:
                'Erstelle private oder öffentliche Vokabellisten mit Wörtern unserer Community. Kombiniere beliebige Sprachpaare: Englisch, Spanisch und Deutsch.',
            },
            step2: {
              title: 'KI ergänzt Wörter',
              description:
                'Fehlt ein Wort? Unsere KI-Agenten erstellen in Echtzeit umfassende Vokabelkarten mit Aussprache, Bildern und Beispielen. Gib Feedback zur Verbesserung.',
            },
            step3: {
              title: 'Mit Quiz lernen',
              description:
                'Teste dich mit Multiple-Choice-Quizzen basierend auf deinen Listen. Verfolge deinen Fortschritt und lerne effektiv.',
            },
          },
          features: {
            title: 'Alles, was du zum Vokabelnlernen brauchst',
            subtitle: 'Starke Features für gemeinsames Lernen',
            personalLists: {
              title: 'Private & Öffentliche Listen',
              description:
                'Pflege eigene Listen oder teile sie mit der Community. Sortiere nach Themen, Schwierigkeit oder Ziel.',
            },
            communityDatabase: {
              title: 'Community-Datenbank',
              description:
                'Jedes KI-generierte Wort steht allen zur Verfügung. Baue auf den Listen anderer auf und erweitere den gemeinsamen Wortschatz.',
            },
            aiGeneration: {
              title: 'Echtzeit-KI',
              description:
                'Erlebe live, wie KI-Agenten Vokabelkarten erstellen – mit Audio, Bildern und Beispielen. Gib Feedback, um jedes Wort zu perfektionieren.',
            },
          },
        },
        search: {
          title: 'Entdecke',
          titleHighlight: 'Neue Wörter',
          subtitle:
            'Suche Wörter in unserer Community-Datenbank oder lass sie von unseren KI-Agenten erstellen',
          sourceLanguage: 'Von',
          targetLanguage: 'Nach',
          selectLanguage: 'Sprache wählen',
          inputPlaceholder: 'Wort eingeben',
          button: 'Suchen',
        },
      },
      es: {
        // informal "tú"
        header: {
          search: 'Buscar',
          notifications: 'Notificaciones',
          account: 'Cuenta',
          profile: 'Perfil',
          language: 'Idioma',
          lightMode: 'Modo claro',
          darkMode: 'Modo oscuro',
          healthDashboard: 'Panel de salud',
          signIn: 'Iniciar sesión',
          signOut: 'Cerrar sesión',
          register: 'Registrarse',
          guestUser: 'Invitado',
          notSignedIn: 'No has iniciado sesión',
        },
        common: {
          welcome: '¡Bienvenido!',
          home: 'Inicio',
          loading: 'Cargando…',
          error: 'Error',
          success: 'Éxito',
          cancel: 'Cancelar',
          confirm: 'Confirmar',
          save: 'Guardar',
          edit: 'Editar',
          delete: 'Eliminar',
          close: 'Cerrar',
        },
        messages: {
          unknownError: 'Algo falló. Por favor, inténtalo de nuevo.',
          loginCredentialsIncorrect:
            'Usuario o contraseña inválidos. Revisa y prueba otra vez.',
          networkError:
            'Error de red. Verifica tu conexión e inténtalo de nuevo.',
          serverError: 'Error del servidor. Inténtalo más tarde.',
          loginFirst: 'Debes iniciar sesión para acceder.',
          sessionExpired: 'Tu sesión expiró. Inicia sesión otra vez.',
        },
        health: {
          dashboard: {
            title: 'Panel de salud',
            refresh: 'Actualizar',
            lastUpdated: 'Última actualización',
            status: {
              excellent: 'Excelente',
              good: 'Bueno',
              poor: 'Malo',
            },
            tiles: {
              backendHealth: 'Estado backend',
              backendHealthDescription: 'Uptime y errores del backend',
              backendResponseTime: 'Latencia',
              backendResponseTimeDescription: 'Latencia promedio del API',
              backendErrorRate: 'Tasa de errores',
              backendErrorRateDescription: 'Errores por minuto',
              jsErrorRate: 'Errores JS',
              jsErrorRateDescription: 'Errores de JavaScript por minuto',
            },
            values: {
              offline: 'Sin conexión',
              noErrors: 'Sin errores',
              errorsPerMinute: 'errores/min',
              milliseconds: 'ms',
            },
          },
        },
        auth: {
          // títulos y encabezados
          signIn: 'Iniciar sesión',
          signInSubtitle: '¡Bienvenido de nuevo! Ingresa a tu cuenta.',
          createAccount: 'Crear cuenta',
          createAccountSubtitle: '¡Regístrate y empieza ya!',
          resetPassword: 'Restablecer contraseña',
          resetPasswordSubtitle:
            'Ingresa tu correo para cambiar tu contraseña.',
          verifyEmail: 'Verificar correo',
          verifyEmailSubtitle: 'Te enviamos un código a {{email}}.',
          userProfile: 'Tu perfil',

          // campos
          username: 'Usuario',
          emailAddress: 'Correo electrónico',
          password: 'Contraseña',
          confirmPassword: 'Confirmar contraseña',
          verificationCode: 'Código de verificación',

          // placeholders
          enterUsername: 'Ingresa tu usuario',
          enterEmail: 'Ingresa tu correo',
          enterPassword: 'Ingresa tu contraseña',
          confirmYourPassword: 'Confirma tu contraseña',
          enterVerificationCode: 'Código de 6 dígitos',

          // botones
          signInButton: 'Entrar',
          signingIn: 'Ingresando…',
          createAccountButton: 'Crear cuenta',
          creatingAccount: 'Creando cuenta…',
          resetPasswordButton: 'Enviar enlace',
          sending: 'Enviando…',
          verifyEmailButton: 'Verificar',
          verifying: 'Verificando…',
          resendCode: 'Reenviar código',
          resendingCode: 'Reenviando…',
          resendInTime: 'Reenviar en {{time}}',
          backToLogin: 'Volver a iniciar sesión',
          updateAccount: 'Actualizar cuenta',
          updateAccountButton: 'Actualizar',
          updatingAccount: 'Actualizando…',
          deleteAccount: 'Eliminar cuenta',

          // links
          dontHaveAccount: '¿No tienes cuenta?',
          createAccountLink: 'Regístrate',
          alreadyHaveAccount: '¿Ya tienes cuenta?',
          signInLink: 'Iniciar sesión',
          forgotPasswordLink: '¿Olvidaste tu contraseña?',
          didntReceiveCode: '¿No llegó el código?',

          // OAuth
          continueWithGoogle: 'Continuar con Google',
          or: 'o',

          // perfil
          manageAccount: 'Administra tu configuración y preferencias',
          accountInformation: 'Info de la cuenta',
          notAvailable: 'No disponible',
          emailStatus: 'Estado del correo',
          verified: 'Verificado',
          notVerified: 'No verificado',
          role: 'Rol',
          sessionStatus: 'Sesión',
          sessionExpiresIn: 'Expira en',
          sessionExpired: 'Sesión expirada',
          noSession: 'Sin sesión',
          invalidSession: 'Sesión inválida',
          preferences: 'Preferencias',
          darkMode: 'Modo oscuro',
          darkModeDescription: 'Cambia entre claro y oscuro',
          accountActions: 'Acciones',
          signOut: 'Cerrar sesión',

          // estados de éxito
          emailSentSuccessfully: '¡Correo enviado con éxito!',
          checkYourEmail: '¡Revisa tu correo!',
          newPasswordSent: 'Te mandamos la nueva contraseña.',
          emailSentIfExists:
            'Si tienes cuenta, recibirás instrucciones pronto.',
          loginSuccessful: '¡Ingresaste correctamente!',
          registrationSuccessful: '¡Registro exitoso! Revisa tu correo.',
          emailVerifiedSuccessfully: '¡Correo verificado!',
          verificationCodeResent: 'Código reenviado.',
          logoutSuccessful: '¡Sesión cerrada!',
          accountDeletedSuccessfully: '¡Cuenta eliminada!',
          updateAccountSuccess: '¡Cuenta actualizada!',

          // errores
          invalidCredentials: 'Datos inválidos. Intenta de nuevo.',
          loginFailed: 'Error al ingresar. Intenta otra vez.',
          unexpectedError: 'Error inesperado. Intenta más tarde.',
          emailNotVerified: 'Verifica tu correo antes de entrar.',
          googleLoginFailed: 'Error con inicio de Google.',
          registrationFailed: 'No se pudo registrar.',
          usernameOrEmailExists: 'Usuario o correo ya existe.',
          resetEmailFailed: 'No se envió el correo.',
          verificationFailed: 'Verificación fallida.',
          invalidVerificationCode: 'Código inválido.',
          resendCodeFailed: 'No se pudo reenviar código.',
          logoutFailed: 'Error al cerrar sesión.',
          accountDeletionFailed: 'No se pudo eliminar cuenta.',
          updateAccountFailed: 'No se pudo actualizar cuenta.',

          // confirmaciones
          deleteAccountConfirm:
            '¿Seguro quieres eliminar tu cuenta? No podrás recuperar nada.',

          // accesibilidad
          showPassword: 'Mostrar contraseña',
          hidePassword: 'Ocultar contraseña',
          resendVerificationCode: 'Reenviar código de verificación',
          passwordOptional: 'Contraseña (opcional)',
        },
        home: {
          hero: {
            title: 'Construye tu vocabulario con',
            titleHighlight: 'aprendizaje comunitario impulsado por IA',
            subtitle:
              'Crea listas personalizadas o mira cómo nuestros agentes de IA generan nuevas palabras en tiempo real con audio, imágenes y ejemplos. Domina inglés, español y alemán con cuestionarios interactivos y aprendizaje colaborativo.',
            ctaButton: 'Empieza ahora',
            stats: {
              wordsCreated: 'Palabras creadas',
              publicLists: 'Listas públicas',
              activeUsers: 'Usuarios activos',
            },
          },
          howItWorks: {
            title: 'Cómo funciona WordWeave',
            subtitle: 'Aprendizaje comunitario de vocabulario en 3 pasos',
            step1: {
              title: 'Crea tus listas',
              description:
                'Genera listas privadas o públicas usando palabras de nuestra base comunitaria. Elige cualquier combinación: inglés, español o alemán.',
            },
            step2: {
              title: 'La IA completa palabras',
              description:
                '¿Falta una palabra? Nuestros agentes de IA crean tarjetas con pronunciación, imágenes y ejemplos al instante. Danos tu feedback para mejorar.',
            },
            step3: {
              title: 'Aprende con quizzes',
              description:
                'Pon a prueba tu vocabulario con quizzes de opción múltiple basados en tus listas. Lleva el registro de tu progreso.',
            },
          },
          features: {
            title: 'Todo lo que necesitas para dominar vocabulario',
            subtitle: 'Funciones potentes para aprender en comunidad',
            personalLists: {
              title: 'Listas privadas y públicas',
              description:
                'Organiza tus propias listas o comparte con todos. Filtra por tema, nivel u objetivo.',
            },
            communityDatabase: {
              title: 'Base comunitaria',
              description:
                'Cada palabra IA-generada se añade para todos. Aprovecha el trabajo de la comunidad y crece junto a ella.',
            },
            aiGeneration: {
              title: 'IA en tiempo real',
              description:
                'Ve en vivo cómo la IA crea tarjetas de vocabulario con audio, imágenes y ejemplos. Tu feedback las perfecciona.',
            },
          },
        },
        search: {
          title: 'Descubre',
          titleHighlight: 'Nuevas Palabras',
          subtitle:
            'Busca palabras en nuestra base comunitaria o deja que nuestros agentes de IA las creen para ti',
          sourceLanguage: 'De',
          targetLanguage: 'A',
          selectLanguage: 'Seleccionar idioma',
          inputPlaceholder: 'Ingresa una palabra',
          button: 'Buscar',
        },
      },
    };

    return (
      translations[languageCode as keyof typeof translations] || translations.en
    );
  }
}
