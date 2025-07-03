import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, map, of } from 'rxjs';

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

  // Available languages
  readonly languages: Language[] = [
    { code: 'en', name: 'English', flag: '🇺🇸' },
    { code: 'es', name: 'Español', flag: '🇪🇸' },
    { code: 'de', name: 'Deutsch', flag: '🇩🇪' },
  ];

  // Current language signal
  private currentLanguageSignal = signal<Language>(this.languages[0]); // English default

  // Translation cache
  private translationCache = new Map<string, any>();

  constructor() {
    // Load saved language preference
    const savedLanguage = localStorage.getItem('selectedLanguage');
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
      localStorage.setItem('selectedLanguage', languageCode);
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
  translate(key: string, params?: { [key: string]: any }): string {
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
  private getNestedTranslation(obj: any, key: string): string | null {
    return key.split('.').reduce((o, i) => o?.[i], obj);
  }

  // Get translations for a language
  private getTranslations(languageCode: string): any {
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
          signOut: 'Sign out',
          signIn: 'Sign in',
          register: 'Register',
          guestUser: 'Guest User',
          notSignedIn: 'Not signed in',
        },
        common: {
          welcome: 'Welcome',
          home: 'Home',
          loading: 'Loading...',
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
          // Error messages
          unknownError: 'An unknown error occurred. Please try again.',
          loginCredentialsIncorrect:
            'Invalid username or password. Please check your credentials and try again.',
          networkError:
            'Network error. Please check your connection and try again.',
          serverError: 'Server error. Please try again later.',

          // Warning messages
          loginFirst: 'Please login first to access this page.',
          sessionExpired: 'Your session has expired. Please login again.',
        },
        auth: {
          // Page titles and headers
          signIn: 'Sign In',
          signInSubtitle: 'Welcome back! Please sign in to your account.',
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
          email: 'Email',
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
          signingIn: 'Signing in...',
          createAccountButton: 'Create Account',
          creatingAccount: 'Creating account...',
          resetPasswordButton: 'Reset Password',
          sending: 'Sending...',
          verifyEmailButton: 'Verify Email',
          verifying: 'Verifying...',
          resendCode: 'Resend Code',
          resendingCode: 'Sending...',
          resendInTime: 'Resend in {{time}}',
          backToLogin: 'Back to Login',
          updateAccount: 'Update Account',
          updateAccountButton: 'Update Account',
          updatingAccount: 'Updating...',
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
          sessionExpired: 'Session expired',
          noSession: 'No session',
          invalidSession: 'Invalid session',
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
              'Create personalized vocabulary lists from our community database, or watch our AI Agents generate new words in real-time. Master any combination of English, Spanish, and German through interactive quizzes and collaborative learning.',
            ctaButton: 'Start Building Vocabulary',
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
                'Build private or public vocabulary lists using words from our community database. Choose any source-target language combination between English, Spanish, and German.',
            },
            step2: {
              title: 'AI Creates Missing Words',
              description:
                "Need a word that doesn't exist yet? Watch our AI Agents generate comprehensive vocabulary cards in real-time with audio, images, and examples. Provide feedback to help improve the results.",
            },
            step3: {
              title: 'Learn with Quizzes',
              description:
                'Test your knowledge with multiple choice quizzes based on your personal vocabulary lists. Track your progress and master new languages effectively.',
            },
          },
          features: {
            title: 'Everything you need to master vocabulary',
            subtitle: 'Powerful features for collaborative language learning',
            personalLists: {
              title: 'Personal & Public Lists',
              description:
                'Create private vocabulary lists for personal study or share public lists with the community. Organize words by themes, difficulty, or learning goals.',
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
          healthDashboard: 'Gesundheits-Dashboard',
          signOut: 'Abmelden',
          signIn: 'Anmelden',
          register: 'Registrieren',
          guestUser: 'Gast-Benutzer',
          notSignedIn: 'Nicht angemeldet',
        },
        common: {
          welcome: 'Willkommen',
          home: 'Startseite',
          loading: 'Wird geladen...',
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
          // Error messages
          unknownError:
            'Ein unbekannter Fehler ist aufgetreten. Bitte versuchen Sie es erneut.',
          loginCredentialsIncorrect:
            'Ungültiger Benutzername oder Passwort. Bitte überprüfen Sie Ihre Anmeldedaten und versuchen Sie es erneut.',
          networkError:
            'Netzwerkfehler. Bitte überprüfen Sie Ihre Verbindung und versuchen Sie es erneut.',
          serverError: 'Serverfehler. Bitte versuchen Sie es später erneut.',

          // Warning messages
          loginFirst:
            'Bitte melden Sie sich zuerst an, um auf diese Seite zuzugreifen.',
          sessionExpired:
            'Ihre Sitzung ist abgelaufen. Bitte melden Sie sich erneut an.',
        },
        auth: {
          // Page titles and headers
          signIn: 'Anmelden',
          signInSubtitle:
            'Willkommen zurück! Bitte melden Sie sich in Ihrem Konto an.',
          createAccount: 'Konto erstellen',
          createAccountSubtitle: 'Erstellen Sie Ihr Konto, um zu beginnen!',
          resetPassword: 'Passwort zurücksetzen',
          resetPasswordSubtitle:
            'Geben Sie Ihre E-Mail-Adresse ein, um Ihr Passwort zurückzusetzen.',
          verifyEmail: 'E-Mail verifizieren',
          verifyEmailSubtitle:
            'Wir haben einen Verifizierungscode an {{email}} gesendet',
          userProfile: 'Benutzerprofil',

          // Form labels
          username: 'Benutzername',
          email: 'E-Mail',
          emailAddress: 'E-Mail-Adresse',
          password: 'Passwort',
          confirmPassword: 'Passwort bestätigen',
          verificationCode: 'Verifizierungscode',

          // Placeholders
          enterEmail: 'Geben Sie Ihre E-Mail-Adresse ein',
          enterPassword: 'Geben Sie Ihr Passwort ein',
          enterUsername: 'Geben Sie Ihren Benutzernamen ein',
          confirmYourPassword: 'Bestätigen Sie Ihr Passwort',
          enterVerificationCode: '6-stelligen Code eingeben',

          // Button labels
          signInButton: 'Anmelden',
          signingIn: 'Anmeldung...',
          createAccountButton: 'Konto erstellen',
          creatingAccount: 'Konto wird erstellt...',
          resetPasswordButton: 'Passwort zurücksetzen',
          sending: 'Senden...',
          verifyEmailButton: 'E-Mail verifizieren',
          verifying: 'Verifizierung...',
          resendCode: 'Code erneut senden',
          resendingCode: 'Senden...',
          resendInTime: 'Erneut senden in {{time}}',
          backToLogin: 'Zurück zur Anmeldung',
          updateAccount: 'Konto aktualisieren',
          updateAccountButton: 'Konto aktualisieren',
          updatingAccount: 'Aktualisierung...',
          deleteAccount: 'Konto löschen',

          // Links and navigation
          dontHaveAccount: 'Haben Sie noch kein Konto?',
          createAccountLink: 'Konto erstellen',
          alreadyHaveAccount: 'Haben Sie bereits ein Konto?',
          signInLink: 'Anmelden',
          forgotPasswordLink: 'Passwort vergessen?',
          didntReceiveCode: 'Code nicht erhalten?',

          // Google OAuth
          continueWithGoogle: 'Mit Google fortfahren',
          or: 'oder',

          // Profile page
          manageAccount:
            'Verwalten Sie Ihre Kontoeinstellungen und -präferenzen',
          accountInformation: 'Kontoinformationen',
          notAvailable: 'Nicht verfügbar',
          emailStatus: 'E-Mail-Status',
          verified: 'Verifiziert',
          notVerified: 'Nicht verifiziert',
          role: 'Rolle',
          sessionStatus: 'Sitzungsstatus',
          sessionExpiresIn: 'Sitzung läuft ab in',
          sessionExpired: 'Sitzung abgelaufen',
          noSession: 'Keine Sitzung',
          invalidSession: 'Ungültige Sitzung',
          preferences: 'Einstellungen',
          darkMode: 'Dunkler Modus',
          darkModeDescription: 'Zwischen hellem und dunklem Design wechseln',
          accountActions: 'Konto-Aktionen',
          signOut: 'Abmelden',

          // Success states
          emailSentSuccessfully: 'E-Mail erfolgreich gesendet!',
          checkYourEmail: 'Überprüfen Sie Ihre E-Mail!',
          newPasswordSent: 'Wir haben Ihnen ein neues Passwort gesendet.',
          emailSentIfExists:
            'Falls ein Konto mit dieser E-Mail existiert, erhalten Sie in Kürze Anweisungen zum Zurücksetzen des Passworts.',

          // Success messages
          loginSuccessful: 'Anmeldung erfolgreich!',
          registrationSuccessful:
            'Registrierung erfolgreich! Bitte überprüfen Sie Ihre E-Mail für den Verifizierungscode.',
          emailVerifiedSuccessfully: 'E-Mail erfolgreich verifiziert!',
          verificationCodeResent: 'Verifizierungscode an Ihre E-Mail gesendet.',
          logoutSuccessful: 'Abmeldung erfolgreich!',
          accountDeletedSuccessfully: 'Konto erfolgreich gelöscht!',
          updateAccountSuccess: 'Konto erfolgreich aktualisiert!',

          // Error messages
          invalidCredentials:
            'Ungültige Anmeldedaten. Bitte versuchen Sie es erneut.',
          loginFailed:
            'Anmeldung fehlgeschlagen. Bitte versuchen Sie es erneut.',
          unexpectedError:
            'Ein unerwarteter Fehler ist aufgetreten. Bitte versuchen Sie es erneut.',
          emailNotVerified:
            'Bitte verifizieren Sie Ihre E-Mail-Adresse vor der Anmeldung.',
          googleLoginFailed:
            'Google-Anmeldung konnte nicht initiiert werden. Bitte versuchen Sie es erneut.',
          registrationFailed:
            'Registrierung fehlgeschlagen. Bitte versuchen Sie es erneut.',
          usernameOrEmailExists:
            'Benutzername oder E-Mail existiert bereits. Bitte verwenden Sie andere Anmeldedaten.',
          resetEmailFailed:
            'E-Mail zum Zurücksetzen konnte nicht gesendet werden. Bitte versuchen Sie es erneut.',
          verificationFailed:
            'Verifizierung fehlgeschlagen. Bitte versuchen Sie es erneut.',
          invalidVerificationCode:
            'Ungültiger Verifizierungscode. Bitte versuchen Sie es erneut.',
          resendCodeFailed:
            'Code konnte nicht erneut gesendet werden. Bitte versuchen Sie es erneut.',
          logoutFailed: 'Abmeldung fehlgeschlagen!',
          accountDeletionFailed:
            'Kontolöschung fehlgeschlagen. Bitte versuchen Sie es erneut.',
          updateAccountFailed:
            'Konto konnte nicht aktualisiert werden. Bitte versuchen Sie es erneut.',

          // Confirmation dialogs
          deleteAccountConfirm:
            'Sind Sie sicher, dass Sie Ihr Konto löschen möchten? Diese Aktion kann nicht rückgängig gemacht werden.',

          // Accessibility labels
          showPassword: 'Passwort anzeigen',
          hidePassword: 'Passwort verbergen',
          resendVerificationCode: 'Verifizierungscode erneut senden',

          // Optional field labels
          passwordOptional: 'Passwort (optional)',
        },
        home: {
          hero: {
            title: 'Erweitern Sie Ihren Wortschatz mit',
            titleHighlight: 'KI-gestütztem Gemeinschaftslernen',
            subtitle:
              'Erstellen Sie personalisierte Vokabellisten aus unserer Community-Datenbank oder schauen Sie zu, wie unsere KI-Agenten neue Wörter in Echtzeit generieren. Meistern Sie jede Kombination aus Englisch, Spanisch und Deutsch durch interaktive Quiz und kollaboratives Lernen.',
            ctaButton: 'Vokabeln lernen starten',
            stats: {
              wordsCreated: 'Wörter erstellt',
              publicLists: 'Öffentliche Listen',
              activeUsers: 'Aktive Benutzer',
            },
          },
          howItWorks: {
            title: 'Wie WordWeave funktioniert',
            subtitle:
              'Community-gesteuertes Vokabellernen in 3 einfachen Schritten',
            step1: {
              title: 'Erstellen Sie Ihre Listen',
              description:
                'Erstellen Sie private oder öffentliche Vokabellisten mit Wörtern aus unserer Community-Datenbank. Wählen Sie jede beliebige Quell-Ziel-Sprachkombination zwischen Englisch, Spanisch und Deutsch.',
            },
            step2: {
              title: 'KI erstellt fehlende Wörter',
              description:
                'Brauchen Sie ein Wort, das noch nicht existiert? Schauen Sie zu, wie unsere KI-Agenten umfassende Vokabelkarten in Echtzeit mit Audio, Bildern und Beispielen erstellen. Geben Sie Feedback, um die Ergebnisse zu verbessern.',
            },
            step3: {
              title: 'Lernen mit Quiz',
              description:
                'Testen Sie Ihr Wissen mit Multiple-Choice-Quiz basierend auf Ihren persönlichen Vokabellisten. Verfolgen Sie Ihren Fortschritt und meistern Sie neue Sprachen effektiv.',
            },
          },
          features: {
            title: 'Alles was Sie brauchen, um Vokabeln zu meistern',
            subtitle: 'Mächtige Funktionen für kollaboratives Sprachenlernen',
            personalLists: {
              title: 'Persönliche & Öffentliche Listen',
              description:
                'Erstellen Sie private Vokabellisten für das persönliche Studium oder teilen Sie öffentliche Listen mit der Community. Organisieren Sie Wörter nach Themen, Schwierigkeit oder Lernzielen.',
            },
            communityDatabase: {
              title: 'Community-Datenbank',
              description:
                'Jedes von unseren KI-Agenten generierte Wort wird allen Benutzern zur Verfügung gestellt. Bauen Sie auf der Arbeit anderer auf und tragen Sie zu einer wachsenden gemeinsamen Vokabel-Ressource bei.',
            },
            aiGeneration: {
              title: 'Echtzeit-KI-Generierung',
              description:
                'Schauen Sie zu, wie unsere KI-Agenten live Vokabelkarten mit Audioaussprache, kontextuellen Bildern und Verwendungsbeispielen erstellen. Geben Sie Feedback, um jedes Wort zu perfektionieren.',
            },
          },
        },
      },
      es: {
        header: {
          search: 'Buscar',
          notifications: 'Notificaciones',
          account: 'Cuenta',
          profile: 'Perfil',
          language: 'Idioma',
          lightMode: 'Modo Claro',
          darkMode: 'Modo Oscuro',
          healthDashboard: 'Panel de Salud',
          signOut: 'Cerrar sesión',
          signIn: 'Iniciar sesión',
          register: 'Registrarse',
          guestUser: 'Usuario Invitado',
          notSignedIn: 'No ha iniciado sesión',
        },
        common: {
          welcome: 'Bienvenido',
          home: 'Inicio',
          loading: 'Cargando...',
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
          // Error messages
          unknownError:
            'Ocurrió un error desconocido. Por favor, inténtalo de nuevo.',
          loginCredentialsIncorrect:
            'Nombre de usuario o contraseña inválidos. Por favor, verifica tus credenciales e inténtalo de nuevo.',
          networkError:
            'Error de red. Por favor, verifica tu conexión e inténtalo de nuevo.',
          serverError: 'Error del servidor. Por favor, inténtalo más tarde.',

          // Warning messages
          loginFirst:
            'Por favor, inicia sesión primero para acceder a esta página.',
          sessionExpired:
            'Tu sesión ha expirado. Por favor, inicia sesión de nuevo.',
        },
        auth: {
          // Page titles and headers
          signIn: 'Iniciar Sesión',
          signInSubtitle:
            '¡Bienvenido de vuelta! Por favor, inicia sesión en tu cuenta.',
          createAccount: 'Crear Cuenta',
          createAccountSubtitle: '¡Crea tu cuenta para comenzar!',
          resetPassword: 'Restablecer Contraseña',
          resetPasswordSubtitle:
            'Ingresa tu correo electrónico para restablecer tu contraseña.',
          verifyEmail: 'Verificar Correo Electrónico',
          verifyEmailSubtitle:
            'Hemos enviado un código de verificación a {{email}}',
          userProfile: 'Perfil de Usuario',

          // Form labels
          username: 'Nombre de usuario',
          email: 'Correo electrónico',
          emailAddress: 'Correo electrónico',
          password: 'Contraseña',
          confirmPassword: 'Confirmar contraseña',
          verificationCode: 'Código de verificación',

          // Placeholders
          enterEmail: 'Ingresa tu correo electrónico',
          enterPassword: 'Ingresa tu contraseña',
          enterUsername: 'Ingresa tu nombre de usuario',
          confirmYourPassword: 'Confirma tu contraseña',
          enterVerificationCode: 'Ingresa el código de 6 dígitos',

          // Button labels
          signInButton: 'Iniciar Sesión',
          signingIn: 'Iniciando sesión...',
          createAccountButton: 'Crear Cuenta',
          creatingAccount: 'Creando cuenta...',
          resetPasswordButton: 'Restablecer Contraseña',
          sending: 'Enviando...',
          verifyEmailButton: 'Verificar Correo Electrónico',
          verifying: 'Verificando...',
          resendCode: 'Reenviar Código',
          resendingCode: 'Enviando...',
          resendInTime: 'Reenviar en {{time}}',
          backToLogin: 'Volver al Inicio de Sesión',
          updateAccount: 'Actualizar Cuenta',
          updateAccountButton: 'Actualizar Cuenta',
          updatingAccount: 'Actualizando...',
          deleteAccount: 'Eliminar Cuenta',

          // Links and navigation
          dontHaveAccount: '¿No tienes una cuenta?',
          createAccountLink: 'Crear cuenta',
          alreadyHaveAccount: '¿Ya tienes una cuenta?',
          signInLink: 'Iniciar sesión',
          forgotPasswordLink: '¿Olvidaste tu contraseña?',
          didntReceiveCode: '¿No recibiste el código?',

          // Google OAuth
          continueWithGoogle: 'Continuar con Google',
          or: 'o',

          // Profile page
          manageAccount:
            'Administra la configuración y preferencias de tu cuenta',
          accountInformation: 'Información de la Cuenta',
          notAvailable: 'No disponible',
          emailStatus: 'Estado del Correo Electrónico',
          verified: 'Verificado',
          notVerified: 'No Verificado',
          role: 'Rol',
          sessionStatus: 'Estado de la Sesión',
          sessionExpiresIn: 'La Sesión Expira En',
          sessionExpired: 'Sesión expirada',
          noSession: 'Sin sesión',
          invalidSession: 'Sesión inválida',
          preferences: 'Preferencias',
          darkMode: 'Modo Oscuro',
          darkModeDescription: 'Cambiar entre temas claro y oscuro',
          accountActions: 'Acciones de la Cuenta',
          signOut: 'Cerrar Sesión',

          // Success states
          emailSentSuccessfully: '¡Correo Electrónico Enviado Exitosamente!',
          checkYourEmail: '¡Revisa tu correo electrónico!',
          newPasswordSent: 'Te hemos enviado una nueva contraseña.',
          emailSentIfExists:
            'Si existe una cuenta con ese correo electrónico, recibirás instrucciones para restablecer la contraseña en breve.',

          // Success messages
          loginSuccessful: '¡Inicio de sesión exitoso!',
          registrationSuccessful:
            '¡Registro exitoso! Por favor, revisa tu correo electrónico para el código de verificación.',
          emailVerifiedSuccessfully:
            '¡Correo electrónico verificado exitosamente!',
          verificationCodeResent:
            'Código de verificación reenviado a tu correo electrónico.',
          logoutSuccessful: '¡Cierre de sesión exitoso!',
          accountDeletedSuccessfully: '¡Cuenta eliminada exitosamente!',
          updateAccountSuccess: '¡Cuenta actualizada exitosamente!',

          // Error messages
          invalidCredentials:
            'Credenciales inválidas. Por favor, inténtalo de nuevo.',
          loginFailed:
            'Error al iniciar sesión. Por favor, inténtalo de nuevo.',
          unexpectedError:
            'Ocurrió un error inesperado. Por favor, inténtalo de nuevo.',
          emailNotVerified:
            'Por favor, verifica tu correo electrónico antes de iniciar sesión.',
          googleLoginFailed:
            'Error al iniciar el inicio de sesión con Google. Por favor, inténtalo de nuevo.',
          registrationFailed:
            'Error en el registro. Por favor, inténtalo de nuevo.',
          usernameOrEmailExists:
            'El nombre de usuario o correo electrónico ya existe. Por favor, usa credenciales diferentes.',
          resetEmailFailed:
            'Error al enviar el correo de restablecimiento. Por favor, inténtalo de nuevo.',
          verificationFailed:
            'Error en la verificación. Por favor, inténtalo de nuevo.',
          invalidVerificationCode:
            'Código de verificación inválido. Por favor, inténtalo de nuevo.',
          resendCodeFailed:
            'Error al reenviar el código. Por favor, inténtalo de nuevo.',
          logoutFailed: '¡Error al cerrar sesión!',
          accountDeletionFailed:
            'Error al eliminar la cuenta. Por favor, inténtalo de nuevo.',
          updateAccountFailed:
            'Error al actualizar la cuenta. Por favor, inténtalo de nuevo.',

          // Confirmation dialogs
          deleteAccountConfirm:
            '¿Estás seguro de que quieres eliminar tu cuenta? Esta acción no se puede deshacer.',

          // Accessibility labels
          showPassword: 'Mostrar contraseña',
          hidePassword: 'Ocultar contraseña',
          resendVerificationCode: 'Reenviar código de verificación',

          // Optional field labels
          passwordOptional: 'Contraseña (opcional)',
        },
        home: {
          hero: {
            title: 'Construye tu vocabulario con',
            titleHighlight: 'aprendizaje comunitario impulsado por IA',
            subtitle:
              'Crea listas de vocabulario personalizadas desde nuestra base de datos comunitaria, o mira cómo nuestros Agentes de IA generan nuevas palabras en tiempo real. Domina cualquier combinación de inglés, español y alemán a través de cuestionarios interactivos y aprendizaje colaborativo.',
            ctaButton: 'Comenzar a construir vocabulario',
            stats: {
              wordsCreated: 'Palabras creadas',
              publicLists: 'Listas públicas',
              activeUsers: 'Usuarios activos',
            },
          },
          howItWorks: {
            title: 'Cómo funciona WordWeave',
            subtitle:
              'Aprendizaje de vocabulario impulsado por la comunidad en 3 simples pasos',
            step1: {
              title: 'Crea tus listas',
              description:
                'Construye listas de vocabulario privadas o públicas usando palabras de nuestra base de datos comunitaria. Elige cualquier combinación de idioma origen-destino entre inglés, español y alemán.',
            },
            step2: {
              title: 'La IA crea palabras faltantes',
              description:
                '¿Necesitas una palabra que aún no existe? Mira cómo nuestros Agentes de IA generan tarjetas de vocabulario completas en tiempo real con audio, imágenes y ejemplos. Proporciona comentarios para ayudar a mejorar los resultados.',
            },
            step3: {
              title: 'Aprende con cuestionarios',
              description:
                'Pon a prueba tu conocimiento con cuestionarios de opción múltiple basados en tus listas de vocabulario personales. Rastrea tu progreso y domina nuevos idiomas de manera efectiva.',
            },
          },
          features: {
            title: 'Todo lo que necesitas para dominar el vocabulario',
            subtitle:
              'Características poderosas para el aprendizaje colaborativo de idiomas',
            personalLists: {
              title: 'Listas personales y públicas',
              description:
                'Crea listas de vocabulario privadas para estudio personal o comparte listas públicas con la comunidad. Organiza palabras por temas, dificultad u objetivos de aprendizaje.',
            },
            communityDatabase: {
              title: 'Base de datos comunitaria',
              description:
                'Cada palabra generada por nuestros Agentes de IA se vuelve disponible para todos los usuarios. Construye sobre el trabajo de otros y contribuye a un recurso de vocabulario compartido en crecimiento.',
            },
            aiGeneration: {
              title: 'Generación de IA en tiempo real',
              description:
                'Mira cómo nuestros Agentes de IA crean tarjetas de vocabulario en vivo con pronunciación de audio, imágenes contextuales y ejemplos de uso. Proporciona comentarios para perfeccionar cada palabra.',
            },
          },
        },
      },
    };

    return (
      translations[languageCode as keyof typeof translations] || translations.en
    );
  }
}
