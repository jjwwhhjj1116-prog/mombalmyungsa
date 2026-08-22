param(
  [string]$EpisodeDir = "episodes/gas-hwalmyeongsu"
)

$ErrorActionPreference = "Stop"

function Get-Sha256([string]$Path) {
  return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

$episode = (Resolve-Path -LiteralPath $EpisodeDir).Path
$storyboardPath = Join-Path $episode "plans/storyboard-v6.json"
$scriptPath = Join-Path $episode "final-script-v6.txt"
$storyboard = Get-Content -Raw -LiteralPath $storyboardPath | ConvertFrom-Json

$windows = @{
  s01=@("vit-v6-u01",0.00,1.80); s02=@("vit-v6-u01",1.80,3.40); s03=@("vit-v6-u01",3.40,5.00)
  s04=@("vit-v6-u02",0.00,1.80); s05=@("vit-v6-u02",2.20,4.80); s06=@("vit-v6-u02",5.40,8.00)
  s07=@("vit-v6-u03",0.00,2.20); s08=@("vit-v6-u03",2.20,5.00); s09=@("vit-v6-u03",5.20,8.00)
  s10=@("vit-v6-u04",0.00,2.60); s11=@("vit-v6-u04",2.80,5.20); s12=@("vit-v6-u04",5.20,8.00)
  s13=@("vit-v6-u05",0.00,2.40); s14=@("vit-v6-u05",2.40,4.80); s15=@("vit-v6-u05",5.00,8.00)
  s16=@("vit-v6-u06",0.00,3.00); s17=@("vit-v6-u06",4.80,7.80)
  s18=@("vit-v6-u07",0.00,2.60); s19=@("vit-v6-u07",2.80,5.40); s20=@("vit-v6-u07",5.40,8.00)
  s21=@("vit-v6-u08",0.00,2.00); s22=@("vit-v6-u08",2.00,5.00); s23=@("vit-v6-u08",5.00,8.00)
  s24=@("vit-v6-u09",1.80,4.80); s25=@("vit-v6-u09",5.20,8.00)
  s26=@("vit-v6-u10",0.80,3.80); s27=@("vit-v6-u10",4.80,7.80)
  s28=@("vit-v6-u11",0.00,2.40); s29=@("vit-v6-u11",2.60,5.00); s30=@("vit-v6-u11",5.00,8.00)
  s31=@("vit-v6-u12",0.00,3.00); s32=@("vit-v6-u12",3.80,6.50); s33=@("vit-v6-u12",5.20,8.00)
  s34=@("vit-v6-u13",0.00,2.50); s35=@("vit-v6-u13",2.70,5.20); s36=@("vit-v6-u13",4.80,7.40); s37=@("vit-v6-u13",6.40,8.00)
}

$sourceByUnit = @{}
$candidateByUnit = @{}
$sourceHashByUnit = @{}
Get-ChildItem -LiteralPath (Join-Path $episode "receipts") -Filter "vit-v6-u*.flow-receipt.json" |
  Where-Object { $_.Name -notmatch "attempt" } |
  ForEach-Object {
    $receipt = Get-Content -Raw -LiteralPath $_.FullName | ConvertFrom-Json
    $sourceRel = [string]$receipt.local_media.path
    $sourceAbs = Join-Path $episode $sourceRel
    if (-not (Test-Path -LiteralPath $sourceAbs)) {
      throw "Missing source media for $($receipt.unit_id): $sourceAbs"
    }
    $actualSha = Get-Sha256 $sourceAbs
    if ($actualSha -ne [string]$receipt.local_media.sha256) {
      throw "Source hash mismatch for $($receipt.unit_id)"
    }
    $sourceByUnit[$receipt.unit_id] = $sourceRel.Replace("\\", "/")
    $candidateByUnit[$receipt.unit_id] = [string]$receipt.media_id
    $sourceHashByUnit[$receipt.unit_id] = $actualSha
  }

$repairUnits = @("vit-v6-u03","vit-v6-u04","vit-v6-u05","vit-v6-u06","vit-v6-u07","vit-v6-u10","vit-v6-u12","vit-v6-u13")
$sentences = @()
foreach ($scene in $storyboard.scenes) {
  $id = [string]$scene.sentence_id
  $w = $windows[$id]
  if ($null -eq $w) { throw "No harvest window for $id" }
  $unit = [string]$w[0]
  $sourceIn = [double]$w[1]
  $sourceOut = [double]$w[2]
  $requiresRepair = $repairUnits -contains $unit
  $repair = if ($unit -eq "vit-v6-u12") {
    [ordered]@{
      required = $true
      severity = "release_blocking"
      method = "tracked_opaque_museum_panels_plus_subject_safe_crop"
      tracked_anchors = @("amber_bottle_neck", "wooden_mannequin_hand", "pharmacy_shelf_plane")
      protected_subjects = @("amber_bottle", "wooden_mannequin_hand")
      source_masks = @(
        [ordered]@{ region = "left_shelf_label_band"; x = 0; y = 540; width = 230; height = 390 },
        [ordered]@{ region = "right_shelf_label_band"; x = 500; y = 540; width = 220; height = 390 }
      )
      acceptance = "zero_readable_or_pseudo_readable_generated_writing_in_every_rendered_frame"
      final_qa_gate = "FAIL_if_any_source_label_remains_visible"
    }
  } elseif ($requiresRepair) {
    [ordered]@{
      required = $true
      severity = "precautionary"
      method = "subject_safe_reframe_and_opaque_evidence_panel_over_any_generated_marks"
      acceptance = "zero_readable_or_pseudo_readable_generated_writing_in_every_rendered_frame"
    }
  } else {
    [ordered]@{ required = $false }
  }

  $sentences += [ordered]@{
    sentence_id = $id
    narration = [string]$scene.narration
    meaning_target = [string]$scene.meaning_target
    motion_carrier = [string]$scene.motion_carrier
    unit_id = $unit
    candidate_id = $candidateByUnit[$unit]
    source_path = $sourceByUnit[$unit]
    source_sha256 = $sourceHashByUnit[$unit]
    source_in = $sourceIn
    source_out = $sourceOut
    source_duration = [math]::Round($sourceOut - $sourceIn, 3)
    speed_ratio = 1.0
    optical_flow = $false
    reject_reason = $null
    native_audio_decision = "replace"
    audio_harvest_window = $null
    native_audio_reason = "native_event_sync_and_speech_music_absence_not_proven_to_two_frames"
    replacement_sfx_anchor = [string]$scene.sound_trigger
    sync_error_frames = $null
    visual_repair = $repair
  }
}

$manifest = [ordered]@{
  schema_version = "body-invention.clip-harvest.v1"
  episode_id = "gas-hwalmyeongsu"
  revision = 21
  stage_id = "10_clip_harvest"
  status = "selected"
  input_hashes = [ordered]@{
    script = Get-Sha256 $scriptPath
    storyboard = Get-Sha256 $storyboardPath
    batch_lock = Get-Sha256 (Join-Path $episode "locks/09-batch-generation.lock.json")
  }
  rules = [ordered]@{
    source_window_seconds = "1_to_3"
    normal_speed_default = $true
    optical_flow_default = $false
    adjacent_sentence_windows_only = $true
    generated_text_allowed = $false
    native_audio_keep_requires_two_frame_sync = $true
    unverified_native_audio_policy = "replace_with_edit_sfx"
  }
  sentence_count = $sentences.Count
  unique_source_count = 13
  reused_source_windows = "adjacent_sentence_subshots_from_the_same_continuous_eight_second_unit_only"
  failed_units = @()
  conditional_pass_units = @()
  mandatory_repairs = @(
    [ordered]@{
      unit_id = "vit-v6-u12"
      sentences = @("s31","s32","s33")
      problem = "pseudo_Korean_modern_pharmacy_shelf_labels"
      action = "apply_tracked_opaque_masks_before_any_selected_frame_enters_the_final_edit"
      acceptance = "zero_readable_or_pseudo_readable_source_writing"
      release_blocked_if_unrepaired = $true
    }
  )
  sentences = $sentences
  approved_by = "internal_visual_harvest_review"
  completed_at = (Get-Date).ToString("o")
}

$outPath = Join-Path $episode "plans/clip-harvest-v6.json"
$manifest | ConvertTo-Json -Depth 16 | Set-Content -LiteralPath $outPath -Encoding utf8NoBOM
Write-Output $outPath
