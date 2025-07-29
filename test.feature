Feature: Authentification utilisateur
  En tant qu'utilisateur
  Je veux pouvoir me connecter à l'application
  Afin d'accéder à mes données personnelles

  Background:
    Given je suis sur la page de connexion

  Scenario: Connexion réussie avec des identifiants valides
    Given j'ai un compte utilisateur avec l'email "user@example.com" et le mot de passe "motdepasse123"
    When je saisis "user@example.com" dans le champ email
    And je saisis "motdepasse123" dans le champ mot de passe
    And je clique sur le bouton "Se connecter"
    Then je suis redirigé vers la page d'accueil
    And je vois le message "Bienvenue !"

  Scenario: Échec de connexion avec un mot de passe incorrect
    Given j'ai un compte utilisateur avec l'email "user@example.com"
    When je saisis "user@example.com" dans le champ email
    And je saisis "mauvais_motdepasse" dans le champ mot de passe
    And je clique sur le bouton "Se connecter"
    Then je reste sur la page de connexion
    And je vois le message d'erreur "Identifiants incorrects"

  Scenario Outline: Validation des champs obligatoires
    When je saisis "<email>" dans le champ email
    And je saisis "<motdepasse>" dans le champ mot de passe
    And je clique sur le bouton "Se connecter"
    Then je vois le message d'erreur "<message_erreur>"

    Examples:
      | email           | motdepasse | message_erreur              |
      |                 | password   | L'email est obligatoire     |
      | user@example.com|            | Le mot de passe est obligatoire |
      |                 |            | Tous les champs sont obligatoires |