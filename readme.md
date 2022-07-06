# Toolkit zu Generierung und Anpassung von xdomea Aussonderungsnachrichten

## Hintergründe

Das Landesarchiv Thüringen entwickelt im Projekt Digitales Magazin - ThELMA - ein Archiv für die digitale Langzeitarchivierung. ThELMA unterstützt auch bei der Übernahme und Archivierung von E-Akten. Genauer werden Aussonderungsnachrichten nach der xdomea-Spezifikation unterstützt. Für die Funktionstests der E-Akten-Übernahme wurden Testdaten benötigt. Die ersten Testnachrichten wurden manuell erstellt. Komplexe Nachrichten konnten so jedoch nur mit großem Aufwand erstellt werden. Aus der Notwendigkeit heraus, wurden deswegen ein Skript entwickelt, das anhand von Musterdateien komplexe Nachrichten generieren können. Mit der Zeit wurden weitere Skripte erstellt, bspw. für den automatischen Austausch der Prozess-ID der Aussonderungsnachrichten. So das mit der Zeit eine kleine Sammlung an nützliche Werkzeugen entstanden ist.

## Nachrichtengenerierung

### Funktionsweise

Das Skript erzeugt eine Anbietung (Aussonderung.Anbieteverzeichnis.0501) und die zugehörige Abgabe (Aussonderung.Aussonderung.0503). Die Inhalte der Nachrichten werden über die Musterdateien konfiguriert. Für beide Nachrichten muss jeweils eine Musterdatei hinterlegt werden. Die Metadaten und Struktur der Schriftgutobjekte (Akten, Vorgänge, Dokumente) werden aus dem Muster der Anbietung extrahiert. Die Muster der Schriftgutobjekte werden vervielfältigt um beliebig komplexe Strukturen zu generieren. Es können auch mehrere Muster für die Schriftgutobjekte angelegt werden, dann werden die Muster zufällig gewählt. Dabei wird darauf geachtet die logische Intigrität der Metadaten zu erhalten. D.h. als Muster für die Vorgänge einer Akte werden nur Vorgangsmuster, die im zugehörigen Aktenmuster definiert wurden, verwendet. Das Gleiche gilt für Vorgänge und Dokumente. Das Muster für die Dokumentenversion wird aus der Abgabe extrahiert oder, wenn nicht vorhanden, vom Skript erzeugt. Die zugehörigen Primärdateien werden zufällig aus den konfigurierten Testdaten gewählt.

### Konfiguration

Die Funktionsweise wird über eine [Konfigurationsdatei](message_generation/config/generator_config.xml) gesteuert. Weiterhin wird eine zugehörige [XML-Schemadatei](message_generation/config/generator_config.xsd) bereitgestellt, mit der überprüft wird, ob die Konfiguration den notwendigen Bedingungen entspricht. XML wurde als Format für die Konfigurationsdatei gewählt, da für die Grundfunktionalität bereits ein XML-Parser benötigt wurde und somit keine weiteren Abhängigkeiten erzeugt wurden.

#### Struktur

In der Strukturkonfiguration kann die Anzahl und Bewertung der Schriftgutobjekte eingestellt werden. Aktuell wird nur die Struktur Akte/Vorgang/Dokument unterstützt.

```
<structure>
  <!-- de: Akten -->
  <files>
    <min_number>2</min_number>
    <max_number>3</max_number>
    <!-- possible values: archive, random -->
    <evaluation>random</evaluation>
    <!-- de: Vorgänge -->
    <processes>
      <min_number>1</min_number>
      <max_number>4</max_number>
      <!-- possible values: inherit, random -->
      <evaluation>random</evaluation>
      <!-- de: Dokumente -->
      <documents>
        <min_number>1</min_number>
        <max_number>6</max_number>
      </documents>
    </processes>
  </files>
</structure>
```

**Anzahl der Schriftgutobjekte**

Für die Gesamtnachricht kann die minimal und maximal Anzahl der enthaltenen Akten festgelegt werden. Weiterhin kann die minimal und maximal Anzahl von in den Akten enthaltenen Vorgängen konfiguriert werden. Das Gleiche gilt für die in den Vorgängen enthaltenen Dokumente. Die minimal Anzahl aller Schriftgutobjekte muss mindestens eins sein.

```
<min_number>2</min_number>
<max_number>3</max_number>
```

**Bewertung der Schriftgutobjekte**

Auf Aktenebene kann zwischen zwei Bewertungsstrategien entschieden werden. Entweder werden alle Akten als archivwürdig gekennzeichnet oder die Bewertung wird zufällig gewählt. Bei einer zufälligen Auswahl wird die erste Akte immer archivwürdig bewertet, damit immer eine gültige Abgabe generiert wird.

```
<structure>
  <!-- de: Akten -->
  <files>
    ...
    <!-- possible values: archive, random -->
    <evaluation>random</evaluation>
    ...
  </files>
</structure>
```

Auf Vorgangsebene kann zwischen zwei Bewertungsstrategien entschieden werden. Entweder die Bewertung der zugehörigen Akte vererbt sich auf alle enthaltenen Vorgänge oder die Bewertung wird zufällig gewählt. Bei einer zufälligen Auswahl wird die erste Vorgang einer Akte immer archivwürdig bewertet, damit immer eine gültige Abgabe generiert wird. Weiterhin wird nur eine zufällige Bewertung gewählt, wenn die übergeordnete Akte als archivwürdig bewertet wurde.

```
<structure>
  ...
    <!-- de: Vorgänge -->
    <processes>
      ...
      <!-- possible values: inherit, random -->
      <evaluation>random</evaluation>
      ...
    </processes>
  ...
</structure>
```

#### xdomea

In der Konfiguration für xdomea kann die Zielversion der Nachrichten und weitere versionsspezifische Einstellungen angepasst werden. Aktuell werden die xdomea Versionen 2.3.0, 2.4.0 und 3.0.0 unterstützt. Um die Zielversion auszuwählen muss die ID im Attribut _target_version_ eingetragen werden.

```
<xdomea target_version="2.3.0">
  <version>
    <id>2.3.0</id>
    <schema>schemes/xdomea_2.3.0/xdomea-Nachrichten-AussonderungDurchfuehren.xsd</schema>
    <file_type_code_list>schemes/xdomea_2.3.0/xdomea-Datentypen.xsd</file_type_code_list>
    <pattern>
      <message_0501>pattern/xdomea_2.3.0/xx_Aussonderung.Anbieteverzeichnis.0501.xml</message_0501>
      <message_0503>pattern/xdomea_2.3.0/xx_Aussonderung.Aussonderung.0503.xml</message_0503>
    </pattern>
  </version>
  <version>
    <id>2.4.0</id>
    <schema>schemes/xdomea_2.4.0/xdomea-Nachrichten-AussonderungDurchfuehren.xsd</schema>
    <file_type_code_list>schemes/xdomea_2.4.0/code_lists/Dateiformat_1.0.xml</file_type_code_list>
    <pattern>
      <message_0501>pattern/xdomea_2.4.0/xx_Aussonderung.Anbieteverzeichnis.0501.xml</message_0501>
      <message_0503>pattern/xdomea_2.4.0/xx_Aussonderung.Aussonderung.0503.xml</message_0503>
    </pattern>
  </version>
  <version>
    <id>3.0.0</id>
    <schema>schemes/xdomea_3.0.0/xdomea-Nachrichten-AussonderungDurchfuehren.xsd</schema>
    <file_type_code_list>schemes/xdomea_3.0.0/code_lists/Dateiformat_1.0.xml</file_type_code_list>
    <pattern>
      <message_0501>pattern/xdomea_3.0.0/xx_Aussonderung.Anbieteverzeichnis.0501.xml</message_0501>
      <message_0503>pattern/xdomea_3.0.0/xx_Aussonderung.Aussonderung.0503.xml</message_0503>
    </pattern>
  </version>
</xdomea>
```

**Versionsspezifische Einstellungen**

In den versionsspezifischen Einstellungen für xdomea kann die Versions-ID, die zugehörige Schemadatei, die Codeliste für Dateiformate und die Nachrichtenmuster für die Generierung konfiguriert werden. Es empfiehlt sich bei Bedarf nur die Pfade der Nachrichtenmuster anzupassen. Die restlichen Werte sind bereits optimal und sollten nur angepasst werden, wenn man die Funktionsweise des Skripts grundlegend versteht. Die verwiesenen Schemadatein sollten ebenfalls nicht ausgetauscht werden. Die Schemadateien, die mit dem Repository ausgeliefert werden, wurden so angepasst, dass für die Validierung keine Online-Ressourcen benötigt werden. Deswegen funktioniert das Skript auch ohne eine Internetverbindung problemlos.

```
<xdomea target_version="3.0.0">
  ...
  <version>
    <id>3.0.0</id>
    <schema>schemes/xdomea_3.0.0/xdomea-Nachrichten-AussonderungDurchfuehren.xsd</schema>
    <file_type_code_list>schemes/xdomea_3.0.0/code_lists/Dateiformat_1.0.xml</file_type_code_list>
    <pattern>
      <message_0501>pattern/xdomea_3.0.0/xx_Aussonderung.Anbieteverzeichnis.0501.xml</message_0501>
      <message_0503>pattern/xdomea_3.0.0/xx_Aussonderung.Aussonderung.0503.xml</message_0503>
    </pattern>
  </version>
  ...
</xdomea>
```