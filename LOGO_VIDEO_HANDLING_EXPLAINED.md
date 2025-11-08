# Brand Logo Overlay - Video Handling Behavior

## 🎯 How It Works Now

The brand logo overlay feature now gives users **TWO OPTIONS** when applying a logo:

### ✅ Option 1: Create New Clip (RECOMMENDED)
- **Original video**: Kept untouched
- **New video**: Created with logo overlay
- **Result**: You get BOTH versions
- **Database**: New clip entry created
- **Filename**: `original_name_branded.mp4`
- **Title**: `Original Title (Branded)`
- **Benefit**: Can compare, undo, or use both versions

### ✅ Option 2: Replace Original
- **Original video**: Deleted from disk
- **New video**: Created with logo, renamed to original filename
- **Result**: Only branded version remains
- **Database**: Same clip entry, file updated
- **Filename**: Same as original (e.g., `short_1.mp4`)
- **Benefit**: Saves disk space, cleaner library

---

## 🔄 User Flow

### When User Clicks "Apply Logo":

```
User triggers logo application
    ↓
Confirmation dialog appears:
┌─────────────────────────────────────────────────┐
│ 🎨 Logo Application Options:                   │
│                                                 │
│ • Click "OK" to CREATE A NEW CLIP with logo    │
│   (keeps original)                              │
│                                                 │
│ • Click "Cancel" to REPLACE ORIGINAL clip      │
│   with logo                                     │
│                                                 │
│ Recommended: Create new clip to keep original  │
└─────────────────────────────────────────────────┘
    ↓
User chooses:
    ↓
┌───────────────────┐              ┌───────────────────┐
│   OK (New Clip)   │              │ Cancel (Replace)  │
└─────────┬─────────┘              └─────────┬─────────┘
          │                                  │
          ▼                                  ▼
  create_new_clip=true           create_new_clip=false
          │                                  │
          ▼                                  ▼
┌─────────────────────┐          ┌─────────────────────┐
│ Creates new file:   │          │ Creates temp file:  │
│ short_1_branded.mp4 │          │ short_1_temp_logo   │
└──────────┬──────────┘          └──────────┬──────────┘
           │                                 │
           ▼                                 ▼
┌─────────────────────┐          ┌─────────────────────┐
│ New clip in DB:     │          │ Delete original:    │
│ ID: 123 (new)       │          │ short_1.mp4         │
│ Title: "... (Brand)"│          └──────────┬──────────┘
│ Path: ...branded    │                     │
└──────────┬──────────┘                     ▼
           │                     ┌─────────────────────┐
           │                     │ Rename temp to orig:│
           │                     │ short_1.mp4         │
           │                     └──────────┬──────────┘
           │                                │
           │                                ▼
           │                     ┌─────────────────────┐
           │                     │ Update DB (same ID):│
           │                     │ Path: short_1.mp4   │
           │                     └──────────┬──────────┘
           │                                │
           ▼                                ▼
    ┌──────────────────────────────────────────┐
    │  User sees result in clip library        │
    └──────────────────────────────────────────┘
```

---

## 📊 Comparison Table

| Aspect | Create New Clip | Replace Original |
|--------|----------------|------------------|
| **Original video** | ✅ Kept | ❌ Deleted |
| **Branded video** | ✅ Created | ✅ Created |
| **Disk space** | Uses more (2 files) | Uses less (1 file) |
| **Clip count** | +1 new clip | Same count |
| **Undo ability** | ✅ Easy (keep original) | ❌ Cannot undo |
| **Database** | New entry | Same entry updated |
| **Filename** | `_branded` suffix | Same as original |
| **Use case** | Testing, comparison | Final production |

---

## 🎬 Examples

### Example 1: Create New Clip (Recommended)

**Before:**
```
Database:
- Clip #1: short_1.mp4 (no logo)

Files:
- short_1.mp4
```

**After applying logo (create new):**
```
Database:
- Clip #1: short_1.mp4 (original, no logo)
- Clip #2: short_1_branded.mp4 (with logo) ← NEW

Files:
- short_1.mp4 (original)
- short_1_branded.mp4(with logo) ← NEW
```

**Result:** User has BOTH versions!

---

### Example 2: Replace Original

**Before:**
```
Database:
- Clip #1: short_1.mp4 (no logo)

Files:
- short_1.mp4
```

**After applying logo (replace):**
```
Database:
- Clip #1: short_1.mp4 (NOW with logo) ← UPDATED

Files:
- short_1.mp4 (NOW contains logo, original deleted) ← REPLACED
```

**Result:** Only branded version exists, original gone.

---

## 💻 API Behavior

### Request with `create_new_clip=true`:
```json
POST /api/v1/clips/1/apply-logo?logo_path=logo.png
{
  "position": "bottom-right",
  "size_percent": 10.0,
  "opacity": 0.8,
  "padding": 20,
  "create_new_clip": true  ← CREATE NEW
}
```

**Response:**
```json
{
  "job_id": "abc-123",
  "status": "completed",
  "result": {
    "new_clip_id": 2,           ← NEW CLIP CREATED
    "new_file_path": "short_1_branded.mp4",
    "original_clip_id": 1,      ← ORIGINAL STILL EXISTS
    "position": "bottom-right",
    "size_percent": 10.0,
    "opacity": 0.8
  }
}
```

---

### Request with `create_new_clip=false`:
```json
POST /api/v1/clips/1/apply-logo?logo_path=logo.png
{
  "position": "bottom-right",
  "size_percent": 10.0,
  "opacity": 0.8,
  "padding": 20,
  "create_new_clip": false  ← REPLACE ORIGINAL
}
```

**Response:**
```json
{
  "job_id": "abc-123",
  "status": "completed",
  "result": {
    "clip_id": 1,                ← SAME CLIP ID
    "file_path": "short_1.mp4",  ← SAME FILENAME
    "position": "bottom-right",
    "size_percent": 10.0,
    "opacity": 0.8,
    "replaced": true             ← INDICATES REPLACEMENT
  }
}
```

---

## 🔧 Backend Implementation Details

### Create New Clip Path:
```python
if create_new_clip:
    # Step 1: Create new file
    output_path = f"{original_stem}_branded.mp4"
    clipper.add_logo(...)  # Creates branded version
    
    # Step 2: Create new database entry
    new_short = Short(
        project_id=project_id,
        file_path=output_path,
        title=f"{original_title} (Branded)",
        # ... copy other fields
    )
    db.add(new_short)
    db.commit()
    
    # Result: Original + New both exist
```

### Replace Original Path:
```python
else:  # Replace original
    # Step 1: Create temp file
    temp_path = f"{original_stem}_temp_logo.mp4"
    clipper.add_logo(...)  # Creates branded version
    
    # Step 2: Delete original
    original_path.unlink()
    
    # Step 3: Rename temp to original name
    temp_path.rename(original_path)
    
    # Step 4: Update database (same ID, same path)
    short.file_path = str(original_path)
    db.commit()
    
    # Result: Only branded version exists
```

---

## 🎯 Recommendations

### ✅ When to Create New Clip:
- Testing different logo positions/sizes
- Want to compare before/after
- Need to keep original for other purposes
- Client approval process (show both versions)
- A/B testing different branding

### ✅ When to Replace Original:
- Final production ready
- Disk space is limited
- Sure about logo settings
- Don't need original anymore
- Simplifying clip library

---

## 🚀 Default Behavior

**Default**: `create_new_clip=false` in API  
**Frontend Dialog**: Recommends creating new clip (OK button)

User gets a choice every time, with guidance towards safer option (create new).

---

## 📝 Chat Feedback

### When Creating New Clip:
```
✅ Logo applied successfully to Highlight 1! New clip being created...

[After completion]
✅ Logo applied - new clip "Highlight 1 (Branded)" created! 
   Original clip preserved.
```

### When Replacing Original:
```
✅ Logo applied successfully to Highlight 1! Original clip being updated...

[After completion]
✅ Logo applied - clip "Highlight 1" updated with logo! 
   ⚠️ Original version replaced.
```

---

## 🔒 File Safety

### Protection Mechanisms:

1. **Temp file approach**: Creates temp file first, only deletes original on success
2. **Transaction safety**: Database updates only after file operations succeed
3. **Error recovery**: If process fails, original remains untouched
4. **User confirmation**: Dialog prevents accidental replacement

### Error Scenarios:

**Scenario 1: Logo processing fails**
```
Original: ✅ Still exists
Branded: ❌ Not created
Database: ✅ Unchanged
Result: No data loss
```

**Scenario 2: Disk full during creation**
```
Original: ✅ Still exists
Process: ❌ Stops before deletion
Database: ✅ Unchanged
Result: Safe failure
```

---

## 💡 Best Practices

### For Users:
1. ✅ **Always create new clip first** for testing
2. ✅ Review branded clip before replacing original
3. ✅ Keep originals until final export
4. ✅ Use replace only for final production
5. ✅ Backup important originals externally

### For Developers:
1. ✅ Default to safer option (create new)
2. ✅ Clear user communication in dialogs
3. ✅ Atomic file operations (temp → rename)
4. ✅ Database transaction safety
5. ✅ Comprehensive error handling

---

## 📊 Summary

| Feature | Status |
|---------|--------|
| **Create new clip option** | ✅ Implemented |
| **Replace original option** | ✅ Implemented |
| **User confirmation dialog** | ✅ Implemented |
| **File safety (temp files)** | ✅ Implemented |
| **Database transaction safety** | ✅ Implemented |
| **Error handling** | ✅ Implemented |
| **Chat feedback** | ✅ Implemented |
| **API parameter** | ✅ `create_new_clip` boolean |

---

## 🎉 Conclusion

The logo overlay feature now provides **user choice** and **safety**:

- ✅ **Flexibility**: Choose between creating new or replacing
- ✅ **Safety**: Temp file approach prevents data loss
- ✅ **Guidance**: Dialog recommends safer option
- ✅ **Transparency**: Clear feedback about what happened
- ✅ **Undo capability**: Keep originals when creating new

**Recommended workflow**: Always create new clip first, review result, then optionally replace original if satisfied.

---

**Last Updated**: 2024  
**Version**: 2.0.0 (with create_new_clip option)  
**Status**: ✅ Production Ready
